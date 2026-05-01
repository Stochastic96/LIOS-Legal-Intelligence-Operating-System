import React from "react";
import { NavigationContainer } from "@react-navigation/native";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { Text, View } from "react-native";
import { SafeAreaProvider } from "react-native-safe-area-context";
import ChatScreen from "./src/screens/ChatScreen";
import LearnScreen from "./src/screens/LearnScreen";
import KnowledgeMapScreen from "./src/screens/KnowledgeMapScreen";
import BrainScreen from "./src/screens/BrainScreen";
import { C } from "./src/theme";

const Tab = createBottomTabNavigator();

const TABS = [
  { name: "Chat",  icon: "chat",  label: "Chat"  },
  { name: "Learn", icon: "learn", label: "Learn" },
  { name: "Map",   icon: "map",   label: "Map"   },
  { name: "Brain", icon: "brain", label: "Brain" },
];

const ICONS: Record<string, string> = {
  Chat: "◎", Learn: "△", Map: "□", Brain: "◈",
};

export default function App() {
  return (
    <SafeAreaProvider>
      <NavigationContainer>
        <Tab.Navigator
          id="MainTabs"
          screenOptions={({ route }) => ({
            headerShown: false,
            freezeOnBlur: false,
            tabBarStyle: {
              backgroundColor: C.s1,
              borderTopWidth: 1,
              borderTopColor: C.border,
              height: 56,
              paddingBottom: 6,
              paddingTop: 4,
            },
            tabBarActiveTintColor: C.accent,
            tabBarInactiveTintColor: C.dim,
            tabBarLabelStyle: {
              fontSize: 10,
              fontWeight: "600",
              letterSpacing: 0.5,
              marginTop: 2,
            },
            tabBarIcon: ({ focused, color }) => (
              <Text style={{ fontSize: 18, color, opacity: focused ? 1 : 0.5 }}>
                {ICONS[route.name]}
              </Text>
            ),
          })}
        >
          <Tab.Screen name="Chat"  component={ChatScreen} />
          <Tab.Screen name="Learn" component={LearnScreen} />
          <Tab.Screen name="Map"   component={KnowledgeMapScreen} />
          <Tab.Screen name="Brain" component={BrainScreen} />
        </Tab.Navigator>
      </NavigationContainer>
    </SafeAreaProvider>
  );
}
