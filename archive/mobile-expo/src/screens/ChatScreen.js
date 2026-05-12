import React, { useState } from 'react';
import { View, TextInput, Button, ScrollView, Text, StyleSheet } from 'react-native';
import { postMessage } from '../api';

export default function ChatScreen() {
  const [query, setQuery] = useState('');
  const [responses, setResponses] = useState([]);

  async function send() {
    if (!query) return;
    try {
      const res = await postMessage('mobile-session', query);
      setResponses((r) => [{ q: query, a: res.answer }, ...r]);
      setQuery('');
    } catch (e) {
      setResponses((r) => [{ q: query, a: 'Error: ' + (e.message || e) }, ...r]);
    }
  }

  return (
    <View style={styles.container}>
      <View style={styles.controls}>
        <TextInput
          style={styles.input}
          placeholder="Ask something..."
          value={query}
          onChangeText={setQuery}
        />
        <Button title="Send" onPress={send} />
      </View>
      <ScrollView style={styles.history}>
        {responses.map((r, i) => (
          <View key={i} style={styles.turn}>
            <Text style={styles.q}>Q: {r.q}</Text>
            <Text style={styles.a}>A: {r.a}</Text>
          </View>
        ))}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 12 },
  controls: { flexDirection: 'row', gap: 8, marginBottom: 8 },
  input: { flex: 1, borderWidth: 1, borderColor: '#ccc', padding: 8, borderRadius: 6 },
  history: { flex: 1 },
  turn: { padding: 10, backgroundColor: '#fffdf8', borderRadius: 8, marginBottom: 8 },
  q: { fontWeight: '600' },
  a: { marginTop: 4 },
});
