import React, { useEffect, useRef } from "react";
import { Animated, StyleSheet, Text, View } from "react-native";
import { C, F, R, S, W } from "../theme";

export default function TypingIndicator() {
  const dots = [
    useRef(new Animated.Value(0.3)).current,
    useRef(new Animated.Value(0.3)).current,
    useRef(new Animated.Value(0.3)).current,
  ];
  useEffect(() => {
    const anims = dots.map((d, i) =>
      Animated.loop(
        Animated.sequence([
          Animated.delay(i * 150),
          Animated.timing(d, { toValue: 1,   duration: 280, useNativeDriver: true }),
          Animated.timing(d, { toValue: 0.3, duration: 280, useNativeDriver: true }),
          Animated.delay(500 - i * 150),
        ])
      )
    );
    anims.forEach((a) => a.start());
    return () => anims.forEach((a) => a.stop());
  }, []);
  return (
    <View style={ti.row}>
      <View style={ti.avatar}><Text style={ti.avatarText}>L</Text></View>
      <View style={ti.bubble}>
        {dots.map((d, i) => (
          <Animated.View key={i} style={[ti.dot, { opacity: d }]} />
        ))}
      </View>
    </View>
  );
}

const ti = StyleSheet.create({
  row:        { flexDirection: "row", alignItems: "center", gap: S.sm, paddingHorizontal: S.md, paddingVertical: S.xs + 2 },
  avatar:     { width: 30, height: 30, borderRadius: R.sm, backgroundColor: C.primary, alignItems: "center", justifyContent: "center" },
  avatarText: { color: C.card, fontSize: F.xs, fontWeight: W.heavy },
  bubble:     { flexDirection: "row", alignItems: "center", gap: 4, backgroundColor: C.card, borderRadius: R.md, paddingHorizontal: S.md, paddingVertical: S.sm, borderWidth: 1, borderColor: C.border },
  dot:        { width: 6, height: 6, borderRadius: 3, backgroundColor: C.primary },
});
