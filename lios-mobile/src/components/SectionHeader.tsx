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
      <View style={styles.labelWrap}>
        <View style={styles.bar} />
        <Text style={styles.label}>{label.toUpperCase()}</Text>
      </View>
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
    marginTop: S.xs,
  },
  labelWrap: {
    flexDirection: "row",
    alignItems: "center",
    gap: 7,
  },
  bar: {
    width: 3,
    height: 14,
    borderRadius: 2,
    backgroundColor: C.primary,
  },
  label: {
    fontSize: F.xs,
    fontWeight: W.bold,
    color: C.mid,
    letterSpacing: 1.4,
  },
});
