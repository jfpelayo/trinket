import { Image } from 'expo-image';
import { ScrollView, StyleSheet, Text, View } from 'react-native';

export default function ShopScreen() {
  const coins = 350;
  // Placeholder prices: replace these with your actual trinket prices.
  const prices = [100, 100, 100, 100, 100, 100, 100, 100, 100];

  return (
    <View style={styles.page}>
      <View style={styles.scene}>
        {/* Ocean background with the ship deck */}
        <Image
          source={require('../../assets/images/ocean-background-deck.png')}
          style={styles.backgroundImage}
          contentFit="fill"
          accessible={false}
        />

        {/* Parrot and Trinket Shop sign */}
        <Image
          source={require('../../assets/images/trinket-shop.png')}
          style={styles.sign}
          contentFit="contain"
          accessibilityLabel="Shop"
        />

        {/* Scroll with editable currency text */}
        <View style={styles.currency}>
          <Image
            source={require('../../assets/images/currency-scroll.png')}
            style={styles.scrollImage}
            contentFit="contain"
            accessible={false}
          />

          <Text style={styles.balance}>
            {coins.toLocaleString()} coins
          </Text>
        </View>
        {/* Barrels and price scrolls, three per row */}
        <ScrollView
          style={styles.barrelArea}
          contentContainerStyle={styles.barrelContent}
          showsVerticalScrollIndicator={false}
        >
          <View style={styles.barrelGrid}>
            {prices.map((price, index) => (
              <View key={index} style={styles.barrelCell}>
                <Image
                  source={require('../../assets/images/barrel.png')}
                  style={styles.barrelImage}
                  contentFit="contain"
                  accessibilityLabel={`Trinket barrel ${index + 1}`}
                />
                <View style={styles.priceScroll}>
                  <Image
                    source={require('../../assets/images/currency-scroll.png')}
                    style={styles.scrollImage}
                    contentFit="contain"
                    accessible={false}
                  />
                  <Text style={styles.priceText} numberOfLines={1} adjustsFontSizeToFit>
                    {price} coins
                  </Text>
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
  barrelArea: {
    position: 'absolute',
    top: '55%',
    bottom: '15%',
    left: '4%',
    right: '4%',
  },
  
  barrelContent: {
    paddingBottom: 16,
  },

  barrelGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
  },

  barrelCell: {
    width: '33.333%',
    padding: 6,
    alignItems: 'center',
    marginBottom: 12,
  },

  priceScroll: {
    width: '100%',
    aspectRatio: 2079 / 756,
    marginTop: 4,
    alignItems: 'center',
    justifyContent: 'center',
  },

  priceText: {
    color: '#663313',
    fontSize: 12,
    fontWeight: 'bold',
    maxWidth: '74%',
    textAlign: 'center',
  },

  barrelImage: {
    width: '100%',
    aspectRatio: 1,
  },
  page: {
    flex: 1,
    backgroundColor: '#087FA3',
    alignItems: 'center',
  },

  scene: {
    flex: 1,
    width: '100%',
    maxWidth: 500,
    position: 'relative',
    overflow: 'hidden',
  },

  sign: {
    position: 'absolute',
    top: '12%',
    left: '6%',
    width: '88%',
    aspectRatio: 1664 / 942,
  },

  currency: {
    position: 'absolute',
    top: '39%',
    left: '21%',
    width: '58%',
    aspectRatio: 2079 / 756,
    alignItems: 'center',
    justifyContent: 'center',
  },

  balance: {
    color: '#663313',
    fontSize: 20,
    fontWeight: 'bold',
  },

  backgroundImage: {
    position: 'absolute',
    top: 0,
    left: 0,
    width: '100%',
    height: '100%',
  },
  
  scrollImage: {
    position: 'absolute',
    top: 0,
    left: 0,
    width: '100%',
    height: '100%',
  },
});