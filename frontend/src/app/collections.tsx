import { Image } from 'expo-image';
import { Link } from 'expo-router';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

export default function CollectionsScreen() {
  const insets = useSafeAreaInsets();
  // Empty display slots until the user's collection is connected to the backend.
  return (
    <View style={styles.page}>
      <View style={styles.scene}>
        <Image source={require('../../assets/images/collection-background.png')}
          style={styles.background} contentFit="fill" accessible={false} />
        <ScrollView contentContainerStyle={[styles.content, {
          paddingTop: Math.max(insets.top + 80, 110),
          paddingBottom: insets.bottom + 110,
        }]} showsVerticalScrollIndicator={false}>
          <View style={styles.heading}>
            <Image source={require('../../assets/images/currency-scroll.png')}
              style={styles.background} contentFit="contain" accessible={false} />
            <Text style={styles.title} accessibilityRole="header">Collections</Text>
          </View>
          <View style={styles.intro}>
            <Text style={styles.subtitle}>Your treasure belongs here</Text>
            <Text style={styles.description}>Collect trinkets in the shop to fill your cabin.</Text>
            <Link href="/shop" style={styles.shopLink}>Visit the shop</Link>
          </View>
          <View style={styles.grid}>
            {Array.from({ length: 9 }, (_, index) => (
              <View key={index} style={styles.cell}>
                <Image source={require('../../assets/images/crate.png')}
                  style={styles.crate} contentFit="contain"
                  accessibilityLabel={`Empty collection slot ${index + 1}`} />
                <View style={styles.label}>
                  <Image source={require('../../assets/images/currency-scroll.png')}
                    style={styles.background} contentFit="contain" accessible={false} />
                  <Text style={styles.labelText}>Empty</Text>
                </View>
              </View>
            ))}
          </View>
        </ScrollView>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: '#663313', alignItems: 'center' },
  scene: { flex: 1, width: '100%', maxWidth: 500, position: 'relative', overflow: 'hidden' },
  background: { position: 'absolute', top: 0, left: 0, width: '100%', height: '100%' },
  content: { paddingHorizontal: 16, alignItems: 'center' },
  heading: { width: '92%', aspectRatio: 2079 / 756, alignItems: 'center', justifyContent: 'center' },
  title: { color: '#663313', fontSize: 28, fontWeight: 'bold', textAlign: 'center' },
  intro: { width: '94%', backgroundColor: '#FFE4A3', borderColor: '#663313', borderWidth: 2,
    borderRadius: 16, padding: 16, marginTop: 16, marginBottom: 24, alignItems: 'center' },
  subtitle: { color: '#663313', fontSize: 18, fontWeight: 'bold', textAlign: 'center' },
  description: { color: '#663313', fontSize: 14, textAlign: 'center', marginTop: 8, lineHeight: 20 },
  shopLink: { color: '#663313', fontSize: 16, fontWeight: 'bold', textDecorationLine: 'underline',
    paddingHorizontal: 16, paddingVertical: 14, marginTop: 4 },
  grid: { width: '100%', flexDirection: 'row', flexWrap: 'wrap' },
  cell: { width: '33.333%', padding: 6, marginBottom: 18, alignItems: 'center' },
  crate: { width: '100%', aspectRatio: 1 },
  label: { width: '100%', aspectRatio: 2079 / 756, alignItems: 'center', justifyContent: 'center' },
  labelText: { color: '#663313', fontSize: 12, fontWeight: 'bold' },
});
