import { useCallback, useEffect, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { productosApi } from '@/modules/productos/store/api'
import {
  fetchCatalogosProducto,
  fetchProductos,
  selectCatalogError,
  selectCatalogStatus,
  selectCategorias,
  selectImpuestos,
  selectProductos,
  selectProductosError,
  selectProductosStatus,
  selectProductosTotalCount,
} from '@/modules/productos/productosSlice'

const DEFAULT_GOBERNANZA_DETAIL = {
  score: 100,
  estado: 'LISTO',
  hallazgos: [],
}

const DEFAULT_GOBERNANZA_ANALISIS = {
  score: 0,
  estado: 'RIESGO',
  readiness: {},
  hallazgos: [],
  metricas: {},
}

const DEFAULT_TRAZABILIDAD = {
  resumen: {
    listas_configuradas: 0,
    listas_activas_vigentes: 0,
    pedidos_venta: 0,
    documentos_compra: 0,
  },
  listas_precio: [],
  uso_documentos: {
    pedidos_venta: { cantidad: 0, ultimos: [] },
    documentos_compra: { cantidad: 0, ultimos: [] },
  },
  alertas: [],
}

const DEFAULT_COLLECTION = {
  count: 0,
  results: [],
}

function useProductoDetail(productoId) {
  const [status, setStatus] = useState('idle')
  const [producto, setProducto] = useState(null)
  const [gobernanza, setGobernanza] = useState(DEFAULT_GOBERNANZA_DETAIL)

  useEffect(() => {
    let active = true

    const loadProducto = async () => {
      setStatus('loading')
      try {
        const [productoResult, gobernanzaResult] = await Promise.allSettled([
          productosApi.getOne(productosApi.endpoints.productos, productoId),
          productosApi.executeDetailAction(productosApi.endpoints.productos, productoId, 'gobernanza'),
        ])

        if (!active) {
          return
        }

        if (productoResult.status !== 'fulfilled') {
          throw productoResult.reason
        }

        setProducto(productoResult.value)
        setGobernanza(
          gobernanzaResult.status === 'fulfilled'
            ? gobernanzaResult.value
            : DEFAULT_GOBERNANZA_DETAIL,
        )
        setStatus('succeeded')
      } catch {
        if (!active) {
          return
        }
        setStatus('failed')
      }
    }

    if (productoId) {
      void loadProducto()
    }

    return () => {
      active = false
    }
  }, [productoId])

  return { status, producto, gobernanza, setProducto, setGobernanza }
}

function useProductoAnalisis(productoId) {
  const [status, setStatus] = useState('idle')
  const [producto, setProducto] = useState(null)
  const [trazabilidad, setTrazabilidad] = useState(DEFAULT_TRAZABILIDAD)
  const [historial, setHistorial] = useState(DEFAULT_COLLECTION)
  const [versiones, setVersiones] = useState(DEFAULT_COLLECTION)
  const [gobernanza, setGobernanza] = useState(DEFAULT_GOBERNANZA_ANALISIS)

  const reload = useCallback(async () => {
    if (!productoId) {
      return null
    }

    setStatus('loading')
    try {
      const [productoResult, trazabilidadResult, historialResult, versionesResult, gobernanzaResult] = await Promise.allSettled([
        productosApi.getOne(productosApi.endpoints.productos, productoId),
        productosApi.executeDetailAction(productosApi.endpoints.productos, productoId, 'trazabilidad'),
        productosApi.executeDetailAction(productosApi.endpoints.productos, productoId, 'historial'),
        productosApi.executeDetailAction(productosApi.endpoints.productos, productoId, 'versiones'),
        productosApi.executeDetailAction(productosApi.endpoints.productos, productoId, 'gobernanza'),
      ])

      if (productoResult.status !== 'fulfilled') {
        throw productoResult.reason
      }

      setProducto(productoResult.value)
      setTrazabilidad(
        trazabilidadResult.status === 'fulfilled'
          ? trazabilidadResult.value
          : DEFAULT_TRAZABILIDAD,
      )
      setHistorial(
        historialResult.status === 'fulfilled'
          ? historialResult.value
          : DEFAULT_COLLECTION,
      )
      setVersiones(
        versionesResult.status === 'fulfilled'
          ? versionesResult.value
          : DEFAULT_COLLECTION,
      )
      setGobernanza(
        gobernanzaResult.status === 'fulfilled'
          ? gobernanzaResult.value
          : DEFAULT_GOBERNANZA_ANALISIS,
      )
      setStatus('succeeded')

      return {
        producto: productoResult.value,
        trazabilidad: trazabilidadResult.status === 'fulfilled' ? trazabilidadResult.value : DEFAULT_TRAZABILIDAD,
        historial: historialResult.status === 'fulfilled' ? historialResult.value : DEFAULT_COLLECTION,
        versiones: versionesResult.status === 'fulfilled' ? versionesResult.value : DEFAULT_COLLECTION,
        gobernanza: gobernanzaResult.status === 'fulfilled' ? gobernanzaResult.value : DEFAULT_GOBERNANZA_ANALISIS,
      }
    } catch (error) {
      setStatus('failed')
      throw error
    }
  }, [productoId])

  useEffect(() => {
    let active = true

    const loadAnalisis = async () => {
      try {
        await reload()
      } catch {
        if (!active) {
          return
        }
      }
    }

    if (productoId) {
      void loadAnalisis()
    }

    return () => {
      active = false
    }
  }, [productoId, reload])

  return {
    status,
    producto,
    trazabilidad,
    historial,
    versiones,
    gobernanza,
    reload,
    setProducto,
    setTrazabilidad,
    setHistorial,
    setVersiones,
    setGobernanza,
  }
}

function useListaPrecioCabecera(listaId) {
  const [status, setStatus] = useState('idle')
  const [lista, setLista] = useState(null)

  const reload = useCallback(async () => {
    if (!listaId) {
      return null
    }

    setStatus('loading')
    try {
      const data = await productosApi.getOne(productosApi.endpoints.listasPrecio, listaId)
      setLista(data)
      setStatus('succeeded')
      return data
    } catch (error) {
      setStatus('failed')
      throw error
    }
  }, [listaId])

  useEffect(() => {
    let active = true

    const loadLista = async () => {
      if (!listaId) {
        return
      }

      setStatus('loading')
      try {
        const data = await productosApi.getOne(productosApi.endpoints.listasPrecio, listaId)
        if (!active) {
          return
        }
        setLista(data)
        setStatus('succeeded')
      } catch {
        if (!active) {
          return
        }
        setStatus('failed')
      }
    }

    void loadLista()

    return () => {
      active = false
    }
  }, [listaId])

  return { status, lista, reload, setLista }
}

function useProductosListado({
  includeInactive = false,
  query = '',
  tipo = 'PRODUCTO',
  categoria = 'ALL',
  page = 1,
  pageSize = 0,
} = {}) {
  const dispatch = useDispatch()
  const productos = useSelector(selectProductos)
  const totalCount = useSelector(selectProductosTotalCount)
  const status = useSelector(selectProductosStatus)
  const error = useSelector(selectProductosError)
  const categorias = useSelector(selectCategorias)

  const reload = useCallback(() => {
    return dispatch(fetchProductos({
      includeInactive,
      query,
      tipo,
      categoria,
      page,
      pageSize,
    }))
  }, [categoria, dispatch, includeInactive, page, pageSize, query, tipo])

  useEffect(() => {
    void reload()
  }, [reload])

  useEffect(() => {
    void dispatch(fetchCatalogosProducto())
  }, [dispatch])

  return {
    productos,
    totalCount,
    status,
    error,
    categorias,
    reload,
  }
}

function useListasPrecioBaseData() {
  const [listas, setListas] = useState([])
  const [monedas, setMonedas] = useState([])
  const [clientes, setClientes] = useState([])
  const [status, setStatus] = useState('idle')

  const reload = useCallback(async () => {
    setStatus('loading')
    try {
      const [listasData, monedasData, clientesData] = await Promise.all([
        productosApi.getList(productosApi.endpoints.listasPrecio),
        productosApi.getList(productosApi.endpoints.monedas),
        productosApi.getList(productosApi.endpoints.clientes),
      ])
      setListas(listasData)
      setMonedas(monedasData)
      setClientes(clientesData)
      setStatus('succeeded')
      return { listas: listasData, monedas: monedasData, clientes: clientesData }
    } catch (error) {
      setStatus('failed')
      throw error
    }
  }, [])

  useEffect(() => {
    let active = true

    const loadBaseData = async () => {
      setStatus('loading')
      try {
        const [listasData, monedasData, clientesData] = await Promise.all([
          productosApi.getList(productosApi.endpoints.listasPrecio),
          productosApi.getList(productosApi.endpoints.monedas),
          productosApi.getList(productosApi.endpoints.clientes),
        ])
        if (!active) {
          return
        }
        setListas(listasData)
        setMonedas(monedasData)
        setClientes(clientesData)
        setStatus('succeeded')
      } catch {
        if (!active) {
          return
        }
        setStatus('failed')
      }
    }

    void loadBaseData()

    return () => {
      active = false
    }
  }, [])

  return {
    listas,
    monedas,
    clientes,
    status,
    reload,
    setListas,
  }
}

function useProductoFormData(productoId) {
  const dispatch = useDispatch()
  const categorias = useSelector(selectCategorias)
  const impuestos = useSelector(selectImpuestos)
  const catalogStatus = useSelector(selectCatalogStatus)
  const catalogError = useSelector(selectCatalogError)
  const [pageStatus, setPageStatus] = useState('idle')

  useEffect(() => {
    if (catalogStatus === 'idle') {
      void dispatch(fetchCatalogosProducto())
    }
  }, [catalogStatus, dispatch])

  const loadProducto = useCallback(async () => {
    if (!productoId) {
      setPageStatus('idle')
      return null
    }

    setPageStatus('loading')
    try {
      const data = await productosApi.getOne(productosApi.endpoints.productos, productoId)
      setPageStatus('succeeded')
      return data
    } catch (error) {
      setPageStatus('failed')
      throw error
    }
  }, [productoId])

  return {
    categorias,
    impuestos,
    catalogStatus,
    catalogError,
    pageStatus,
    loadProducto,
  }
}

export {
  useListaPrecioCabecera,
  useListasPrecioBaseData,
  useProductoFormData,
  useProductoAnalisis,
  useProductoDetail,
  useProductosListado,
}
