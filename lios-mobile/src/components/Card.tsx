import React from "react";
import { StyleProp, StyleSheet, View, ViewStyle } from "react-native";
import { C, R, S } from "../theme";

interface Props {
  children: React.ReactNode;
  style?: StyleProp<ViewStyle>;
  padding?: number;
  surface?: "s1" | "s2" | "s3";
}

export default function Card({ children, style, padding = S.md, surface = "s1" }: Props) {
  const bg = surface === "s3" ? C.s3 : surface === "s2" ? C.s2 : C.s1;
  return (
    <View style={[styles.card, { backgroundColor: bg, padding }, style]}>
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    borderRadius: R.md,
    borderWidth: 1,
    borderColor: C.border,
  },
});
