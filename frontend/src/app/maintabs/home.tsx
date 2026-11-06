import { Text, View } from 'react-native';
import { f1 } from '@/constants/theme'; 
import PageBackground from '@/components/pagebackground';

export default function DashboardScreen() {
  return (
    <PageBackground>
      <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center'}}>
        <Text style={{ color: '#fdf7f7', fontSize: 30, fontFamily: f1 }}>Home Not Complete!</Text>
      </View>
    </PageBackground>
  );
}
