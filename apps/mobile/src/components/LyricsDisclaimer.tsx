import { StyleSheet, Text, View } from "react-native";

import { colors, LYRICS_DISCLAIMER } from "../theme";

export function LyricsDisclaimer() {
  return (
    <View style={styles.box}>
      <Text style={styles.text}>{LYRICS_DISCLAIMER}</Text>
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
