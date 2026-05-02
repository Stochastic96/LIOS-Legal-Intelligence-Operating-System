import React from "react";
import { NavigationContainer } from "@react-navigation/native";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { Feather } from "@expo/vector-icons";
import ChatScreen from "./src/screens/ChatScreen";
import LearnScreen from "./src/screens/LearnScreen";
import KnowledgeMapScreen from "./src/screens/KnowledgeMapScreen";
import BrainScreen from "./src/screens/BrainScreen";
import { C, S } from "./src/theme";

const Tab = createBottomTabNavigator();

type FeatherName = React.ComponentProps<typeof Feather>["name"];

const TAB_ICONS: Record<string, FeatherName> = {
  Chat:  "message-circle",
  Learn: "book-open",
  Map:   "map",
  Brain: "cpu",
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
              height: 60,
              paddingBottom: S.sm,
              paddingTop: S.xs,
            },
            tabBarActiveTintColor: C.accent,
            tabBarInactiveTintColor: C.dim,
            tabBarLabelStyle: {
              fontSize: 10,
              fontWeight: "600",
              letterSpacing: 0.8,
              marginTop: 2,
            },
            tabBarIcon: ({ focused, color }) => (
              <Feather
                name={TAB_ICONS[route.name]}
                size={22}
                color={color}
                style={{ opacity: focused ? 1 : 0.55 }}
              />
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
