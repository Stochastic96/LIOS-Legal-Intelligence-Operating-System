import React, { useState, useEffect } from 'react';
import { View, TextInput, Button, Text, StyleSheet } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { DEFAULT_LIOS_BASE_URL, DEFAULT_API_KEY } from '../api';

export default function SettingsScreen() {
  const [baseUrl, setBaseUrl] = useState(DEFAULT_LIOS_BASE_URL === 'http://YOUR_MACHINE_IP:8000' ? '' : DEFAULT_LIOS_BASE_URL);
  const [apiKey, setApiKey] = useState(DEFAULT_API_KEY || '');

  useEffect(() => {
    (async () => {
      const b = await AsyncStorage.getItem('LIOS_BASE_URL');
      const k = await AsyncStorage.getItem('LIOS_API_KEY');
      if (b) setBaseUrl(b);
      if (k) setApiKey(k);
    })();
  }, []);

  async function save() {
    await AsyncStorage.setItem('LIOS_BASE_URL', baseUrl);
    await AsyncStorage.setItem('LIOS_API_KEY', apiKey);
    alert('Saved');
  }

  return (
    <View style={styles.container}>
      <Text style={styles.label}>LIOS Base URL</Text>
      <TextInput style={styles.input} value={baseUrl} onChangeText={setBaseUrl} placeholder="http://192.168.x.x:8000" />
      <Text style={styles.label}>API Key (optional)</Text>
      <TextInput style={styles.input} value={apiKey} onChangeText={setApiKey} placeholder="API Key" />
      <Button title="Save" onPress={save} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 12 },
  label: { fontWeight: '600', marginTop: 8 },
  input: { borderWidth: 1, borderColor: '#ccc', padding: 8, borderRadius: 6, marginBottom: 8 },
});
