import { StyleSheet, Text, View } from "react-native";

import { colors, DISCLAIMER } from "../theme";

export function MeaningDisclaimer() {
  return (
    <View style={styles.box}>
      <Text style={styles.text}>{DISCLAIMER}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  box: {
    backgroundColor: colors.chip,
    borderRadius: 10,
    padding: 10,
  },
  text: {
    color: colors.muted,
    fontSize: 12,
    fontStyle: "italic",
  },
});
