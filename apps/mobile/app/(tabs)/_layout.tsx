import { Tabs } from "expo-router";
import { Text } from "react-native";

import { colors } from "../../src/theme";

function TabIcon({ label, focused }: { label: string; focused: boolean }) {
  return (
    <Text style={{ color: focused ? colors.saffron : colors.muted, fontSize: 12, fontWeight: "700" }}>
      {label}
    </Text>
  );
}

export default function TabsLayout() {
  return (
    <Tabs
      screenOptions={{
        headerStyle: { backgroundColor: colors.parchment },
        headerTintColor: colors.maroon,
        headerTitleStyle: { fontFamily: "NotoSerif_700Bold" },
        tabBarStyle: { backgroundColor: colors.card, borderTopColor: colors.line },
        tabBarActiveTintColor: colors.saffron,
        tabBarInactiveTintColor: colors.muted,
        sceneStyle: { backgroundColor: colors.parchment },
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: "Saha",
          tabBarLabel: "Search",
          tabBarIcon: ({ focused }) => <TabIcon label="ॐ" focused={focused} />,
        }}
      />
      <Tabs.Screen
        name="saved"
        options={{
          title: "Saved",
          tabBarLabel: "Saved",
          tabBarIcon: ({ focused }) => <TabIcon label="✦" focused={focused} />,
        }}
      />
    </Tabs>
  );
}
