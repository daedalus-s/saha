import { Pressable, StyleSheet, Text, View } from "react-native";

import { colors } from "../theme";
import { scriptLabel } from "../utils/scripts";

type Props = {
  scripts: string[];
  selected: string | null;
  onSelect: (script: string | null) => void;
  includeAll?: boolean;
};

export function ScriptChips({ scripts, selected, onSelect, includeAll = true }: Props) {
  const unique = [...(includeAll ? ["all"] : []), ...Array.from(new Set(scripts))];
  return (
    <View style={styles.row}>
      {unique.map((script) => {
        const value = script === "all" ? null : script;
        const active = selected === value;
        return (
          <Pressable
            key={script}
            onPress={() => onSelect(value)}
            style={[styles.chip, active && styles.active]}
          >
            <Text style={[styles.label, active && styles.activeLabel]}>
              {script === "all" ? "All scripts" : scriptLabel(script)}
            </Text>
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
  },
  chip: {
    backgroundColor: colors.chip,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 999,
  },
  active: {
    backgroundColor: colors.chipActive,
  },
  label: {
    color: colors.ink,
    fontSize: 13,
  },
  activeLabel: {
    color: "#fff",
  },
});
