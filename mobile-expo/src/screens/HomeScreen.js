import React from 'react';
import { View, Text, Button, StyleSheet } from 'react-native';

export default function HomeScreen({ navigation }) {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>LIOS Mobile</Text>
      <Text style={styles.subtitle}>Quick access to chat and learning features</Text>
      <View style={{ height: 12 }} />
      <Button title="Open Chat" onPress={() => navigation.navigate('Chat')} />
      <View style={{ height: 8 }} />
      <Button title="Next Question" onPress={() => navigation.navigate('NextQuestion')} />
      <View style={{ height: 8 }} />
      <Button title="Settings" onPress={() => navigation.navigate('Settings')} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 16, justifyContent: 'center' },
  title: { fontSize: 28, fontWeight: '700', textAlign: 'center' },
  subtitle: { textAlign: 'center', color: '#666', marginTop: 8 },
});
