import React from "react";
import { StyleSheet, Text, View } from "react-native";
import { C, F, S, W } from "../theme";

interface Props {
  label: string;
  right?: React.ReactNode;
}

export default function SectionHeader({ label, right }: Props) {
  return (
    <View style={styles.row}>
      <Text style={styles.label}>{label.toUpperCase()}</Text>
      {right}
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: S.sm,
  },
  label: {
    fontSize: F.xs,
    fontWeight: W.bold,
    color: C.mid,
    letterSpacing: 1.2,
  },
});
