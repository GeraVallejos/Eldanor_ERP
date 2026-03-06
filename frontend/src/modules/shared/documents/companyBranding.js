import { api } from '@/api/client'

const brandingCache = new Map()

function blobToDataUrl(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onloadend = () => resolve(String(reader.result || ''))
    reader.onerror = reject
    reader.readAsDataURL(blob)
  })
}

function loadImage(src) {
  return new Promise((resolve, reject) => {
    const img = new window.Image()
    img.onload = () => resolve(img)
    img.onerror = reject
    img.src = src
  })
}

function findOpaqueBounds(imageData, width, height, alphaThreshold = 8) {
  const data = imageData.data
  let top = height
  let left = width
  let right = -1
  let bottom = -1

  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      const alpha = data[(y * width + x) * 4 + 3]
      if (alpha > alphaThreshold) {
        if (x < left) left = x
        if (x > right) right = x
        if (y < top) top = y
        if (y > bottom) bottom = y
      }
    }
  }

  if (right < left || bottom < top) {
    return null
  }

  return {
    left,
    top,
    width: right - left + 1,
    height: bottom - top + 1,
  }
}

async function normalizeLogoForPdf(logoBlob) {
  if (!logoBlob || logoBlob.size === 0) {
    return null
  }

  const sourceDataUrl = await blobToDataUrl(logoBlob)

  try {
    const image = await loadImage(sourceDataUrl)
    const canvas = document.createElement('canvas')
    const width = image.naturalWidth || image.width || 0
    const height = image.naturalHeight || image.height || 0

    if (!width || !height) {
      return sourceDataUrl
    }

    canvas.width = width
    canvas.height = height

    const context = canvas.getContext('2d')
    if (!context) {
      return sourceDataUrl
    }

    context.clearRect(0, 0, width, height)
    context.drawImage(image, 0, 0, width, height)

    const imageData = context.getImageData(0, 0, width, height)
    const bounds = findOpaqueBounds(imageData, width, height)

    if (!bounds) {
      return canvas.toDataURL('image/png')
    }

    const croppedCanvas = document.createElement('canvas')
    croppedCanvas.width = bounds.width
    croppedCanvas.height = bounds.height

    const croppedContext = croppedCanvas.getContext('2d')
    if (!croppedContext) {
      return canvas.toDataURL('image/png')
    }

    croppedContext.drawImage(
      canvas,
      bounds.left,
      bounds.top,
      bounds.width,
      bounds.height,
      0,
      0,
      bounds.width,
      bounds.height,
    )

    return croppedCanvas.toDataURL('image/png')
  } catch {
    return sourceDataUrl
  }
}

function resolveCacheKey(user) {
  return String(user?.empresa_id || 'default')
}

export function clearCompanyDocumentBrandingCache(empresaId) {
  if (!empresaId) {
    brandingCache.clear()
    return
  }

  brandingCache.delete(String(empresaId))
}

export async function getCompanyDocumentBranding({ user, forceRefresh = false } = {}) {
  const cacheKey = resolveCacheKey(user)
  const cached = brandingCache.get(cacheKey)

  if (!forceRefresh && cached?.logo) {
    return cached
  }

  let logoDataUrl = null

  try {
    const { data: logoBlob } = await api.get('/auth/empresa-logo/', {
      responseType: 'blob',
      suppressGlobalErrorToast: true,
    })

    if (logoBlob && logoBlob.size > 0) {
      logoDataUrl = await normalizeLogoForPdf(logoBlob)
    }
  } catch {
    // Si no hay logo disponible, el documento se genera sin imagen.
  }

  const branding = {
    empresaId: user?.empresa_id || null,
    nombre: user?.empresa_nombre || 'Mi Empresa',
    logo: logoDataUrl || null,
  }

  brandingCache.set(cacheKey, branding)
  return branding
}
