import { Linking, Modal, Pressable, StyleSheet, Text, View } from "react-native";

import { API_URL } from "../api/client";
import { colors } from "../theme";

type Props = {
  visible: boolean;
  onContinue: () => void;
  onNotNow: () => void;
};

export function ConsentSheet({ visible, onContinue, onNotNow }: Props) {
  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onNotNow}>
      <View style={styles.backdrop}>
        <View style={styles.card}>
          <Text style={styles.title}>How Saha works with your data</Text>
          <Text style={styles.body}>
            Before we search, we need your explicit permission to share data with third parties,
            including third-party AI.
          </Text>
          <Text style={styles.body}>
            The sloka or mantra name you type is sent to our server and then to a web search
            provider so we can find candidate pages. We fetch those pages on the server. Page text
            (and your search name) may be sent to an AI language-model provider to extract verses.
            If you later tap Show meaning, verse text is sent to an AI language-model provider to
            generate an English meaning.
          </Text>
          <Text style={styles.body}>
            We do not sell this data. You can withdraw permission on the Search screen; new searches
            and meanings will stop until you agree again.
          </Text>
          <Pressable onPress={() => Linking.openURL(`${API_URL}/privacy`)}>
            <Text style={styles.link}>Privacy policy</Text>
          </Pressable>
          <Pressable onPress={() => Linking.openURL(`${API_URL}/terms`)}>
            <Text style={styles.link}>Terms of use</Text>
          </Pressable>
          <Pressable style={styles.primary} onPress={onContinue}>
            <Text style={styles.primaryLabel}>Continue</Text>
          </Pressable>
          <Pressable style={styles.secondary} onPress={onNotNow}>
            <Text style={styles.secondaryLabel}>Not now</Text>
          </Pressable>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: "rgba(43, 33, 24, 0.45)",
    justifyContent: "center",
    padding: 20,
  },
  card: {
    backgroundColor: colors.card,
    borderRadius: 16,
    padding: 20,
    gap: 12,
    borderWidth: 1,
    borderColor: colors.line,
  },
  title: {
    fontFamily: "NotoSerif_700Bold",
    fontSize: 20,
    color: colors.maroon,
  },
  body: {
    color: colors.ink,
    fontSize: 14,
    lineHeight: 21,
  },
  link: {
    color: colors.saffron,
    fontSize: 14,
  },
  primary: {
    backgroundColor: colors.saffron,
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: "center",
    marginTop: 4,
  },
  primaryLabel: {
    color: "#fff",
    fontWeight: "700",
  },
  secondary: {
    alignItems: "center",
    paddingVertical: 8,
  },
  secondaryLabel: {
    color: colors.muted,
    fontSize: 15,
  },
});
