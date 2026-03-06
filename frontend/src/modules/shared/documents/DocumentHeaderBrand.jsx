import { Image, StyleSheet, Text, View } from '@react-pdf/renderer'

const styles = StyleSheet.create({
  container: {
    width: 130,
    alignItems: 'center',
  },
  logoWrap: {
    width: 90,
    height: 45,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 4,
  },
  logo: {
    width: 90,
    height: 45,
    objectFit: 'contain',
  },
  companyName: {
    width: 130,
    color: '#6B7280',
    fontSize: 9,
    lineHeight: 1.3,
    textAlign: 'center',
  },
})

function resolveNameFontSize(companyName) {
  const length = String(companyName || '').trim().length
  if (length > 40) return 7.5
  if (length > 28) return 8
  return 9
}

function DocumentHeaderBrand({ companyName, logoSrc, style }) {
  return (
    <View style={[styles.container, style]}>
      {logoSrc ? (
        <View style={styles.logoWrap}>
          <Image src={logoSrc} style={styles.logo} />
        </View>
      ) : null}
      <Text style={[styles.companyName, { fontSize: resolveNameFontSize(companyName) }]}>
        {companyName || 'Empresa'}
      </Text>
    </View>
  )
}

export default DocumentHeaderBrand
