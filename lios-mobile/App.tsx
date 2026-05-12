import React from "react";
import { NavigationContainer } from "@react-navigation/native";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { Feather } from "@expo/vector-icons";
import { StatusBar } from "expo-status-bar";
import ChatScreen from "./src/screens/ChatScreen";
import LearnScreen from "./src/screens/LearnScreen";
import IntelligenceScreen from "./src/screens/IntelligenceScreen";
import { C, F, S, W } from "./src/theme";

const Tab = createBottomTabNavigator();

type FeatherName = React.ComponentProps<typeof Feather>["name"];

const TAB_ICONS: Record<string, FeatherName> = {
  Assistent:   "message-square",
  Lernchat:    "book-open",
  Intelligenz: "activity",
};

export default function App() {
  return (
    <SafeAreaProvider>
      <StatusBar style="dark" backgroundColor={C.card} />
      <NavigationContainer>
        <Tab.Navigator
          id="MainTabs"
          screenOptions={({ route }) => ({
            headerShown: false,
            freezeOnBlur: false,
            tabBarStyle: {
              backgroundColor: C.card,
              borderTopWidth: 1,
              borderTopColor: C.border,
              height: 62,
              paddingBottom: S.sm,
              paddingTop: S.xs + 2,
            },
            tabBarActiveTintColor:   C.primary,
            tabBarInactiveTintColor: C.dim,
            tabBarLabelStyle: {
              fontSize: 10,
              fontWeight: W.semi,
              letterSpacing: 0.6,
              marginTop: 1,
            },
            tabBarIcon: ({ focused, color }) => (
              <Feather
                name={TAB_ICONS[route.name]}
                size={21}
                color={color}
                style={{ opacity: focused ? 1 : 0.5 }}
              />
            ),
          })}
        >
          <Tab.Screen name="Assistent"   component={ChatScreen} />
          <Tab.Screen name="Lernchat"    component={LearnScreen} />
          <Tab.Screen name="Intelligenz" component={IntelligenceScreen} />
        </Tab.Navigator>
      </NavigationContainer>
    </SafeAreaProvider>
  );
}
