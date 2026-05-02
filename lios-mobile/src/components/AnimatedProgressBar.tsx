import React, { useEffect, useRef } from "react";
import { Animated, StyleSheet, View } from "react-native";
import { C, R } from "../theme";

interface Props {
  value: number;   // 0-100
  color?: string;
  height?: number;
  bgColor?: string;
  duration?: number;
}

export default function AnimatedProgressBar({
  value,
  color = C.accent,
  height = 5,
  bgColor = C.s2,
  duration = 600,
}: Props) {
  const widthAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(widthAnim, {
      toValue: Math.min(100, Math.max(0, value)),
      duration,
      useNativeDriver: false,
    }).start();
  }, [value, duration]);

  const animatedWidth = widthAnim.interpolate({
    inputRange: [0, 100],
    outputRange: ["0%", "100%"],
  });

  return (
    <View style={[styles.track, { height, backgroundColor: bgColor, borderRadius: height / 2 }]}>
      <Animated.View
        style={[
          styles.fill,
          {
            width: animatedWidth,
            height,
            backgroundColor: color,
            borderRadius: height / 2,
          },
        ]}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  track: { overflow: "hidden" },
  fill: {},
});
