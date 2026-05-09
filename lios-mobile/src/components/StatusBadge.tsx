import React from "react";
import { StyleSheet, Text, View } from "react-native";
import { F, R, W } from "../theme";

interface Props {
  label: string;
  color: string;
  bgColor: string;
  bordered?: boolean;
}

export default function StatusBadge({ label, color, bgColor, bordered }: Props) {
  return (
    <View style={[styles.badge, { backgroundColor: bgColor }, bordered && { borderWidth: 1, borderColor: color + "55" }]}>
      <Text style={[styles.text, { color }]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    borderRadius: R.xs,
    paddingHorizontal: 8,
    paddingVertical: 3,
    alignSelf: "flex-start",
  },
  text: {
    fontSize: F.xs,
    fontWeight: W.semi,
    letterSpacing: 0.5,
  },
});
