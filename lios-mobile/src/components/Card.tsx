import React from "react";
import { StyleProp, StyleSheet, View, ViewStyle } from "react-native";
import { C, R, S } from "../theme";

interface Props {
  children: React.ReactNode;
  style?: StyleProp<ViewStyle>;
  padding?: number;
  surface?: "card" | "s2" | "s3";
  accent?: boolean;
}

export default function Card({ children, style, padding = S.md, surface = "card", accent }: Props) {
  const bg = surface === "s3" ? C.s3 : surface === "s2" ? C.s2 : C.card;
  return (
    <View style={[styles.card, { backgroundColor: bg, padding }, accent && styles.accent, style]}>
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    borderRadius: R.md,
    borderWidth: 1,
    borderColor: C.border,
    shadowColor: "#001F6B",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.06,
    shadowRadius: 4,
    elevation: 2,
  },
  accent: {
    borderLeftWidth: 3,
    borderLeftColor: C.primary,
  },
});
