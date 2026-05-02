import React from "react";
import { StyleSheet, Text, View } from "react-native";
import { F, R, W } from "../theme";

interface Props {
  label: string;
  color: string;
  bgColor: string;
}

export default function StatusBadge({ label, color, bgColor }: Props) {
  return (
    <View style={[styles.badge, { backgroundColor: bgColor }]}>
      <Text style={[styles.text, { color }]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    borderRadius: R.full,
    paddingHorizontal: 10,
    paddingVertical: 3,
    alignSelf: "flex-start",
  },
  text: {
    fontSize: F.xs,
    fontWeight: W.semi,
    letterSpacing: 0.4,
  },
});
