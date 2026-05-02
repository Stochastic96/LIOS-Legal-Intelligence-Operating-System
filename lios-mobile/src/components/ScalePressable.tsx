import React, { useRef } from "react";
import { Animated, Pressable, StyleProp, ViewStyle } from "react-native";

interface Props {
  onPress?: () => void;
  onLongPress?: () => void;
  disabled?: boolean;
  style?: StyleProp<ViewStyle>;
  children: React.ReactNode;
  scale?: number;
}

export default function ScalePressable({
  onPress,
  onLongPress,
  disabled,
  style,
  children,
  scale = 0.95,
}: Props) {
  const anim = useRef(new Animated.Value(1)).current;

  const pressIn = () =>
    Animated.timing(anim, { toValue: scale, duration: 60, useNativeDriver: true }).start();

  const pressOut = () =>
    Animated.spring(anim, { toValue: 1, useNativeDriver: true, speed: 24, bounciness: 4 }).start();

  return (
    <Pressable
      onPress={onPress}
      onLongPress={onLongPress}
      onPressIn={pressIn}
      onPressOut={pressOut}
      disabled={disabled}
    >
      <Animated.View style={[style, { transform: [{ scale: anim }], opacity: disabled ? 0.4 : 1 }]}>
        {children}
      </Animated.View>
    </Pressable>
  );
}
