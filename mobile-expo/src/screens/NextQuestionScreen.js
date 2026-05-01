import React, { useState } from 'react';
import { View, Text, Button, StyleSheet } from 'react-native';
import { getNextQuestion, submitFeedback } from '../api';

export default function NextQuestionScreen() {
  const [q, setQ] = useState(null);

  async function load() {
    try {
      const res = await getNextQuestion('mobile-session');
      setQ(res);
    } catch (e) {
      setQ({ question: 'Error: ' + (e.message || e) });
    }
  }

  async function sendFeedback(type) {
    try {
      const payload = {
        session_id: 'mobile-session',
        turn_id: 'turn-1',
        response: type,
        feedback_text: null,
        confidence_level: 0.8,
      };
      await submitFeedback(payload);
      load();
    } catch (e) {
      // ignore
    }
  }

  return (
    <View style={styles.container}>
      <Button title="Load Next Question" onPress={load} />
      {q && (
        <View style={styles.card}>
          <Text style={styles.title}>Question</Text>
          <Text>{q.question}</Text>
          <Text style={{ color: '#666' }}>{q.explanation}</Text>
          <View style={{ flexDirection: 'row', marginTop: 8 }}>
            <Button title="Correct" onPress={() => sendFeedback('correct')} />
            <View style={{ width: 8 }} />
            <Button title="Incorrect" onPress={() => sendFeedback('incorrect')} />
          </View>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 12 },
  card: { padding: 12, backgroundColor: '#eef7f6', borderRadius: 8, marginTop: 12 },
  title: { fontWeight: '700', marginBottom: 6 },
});
