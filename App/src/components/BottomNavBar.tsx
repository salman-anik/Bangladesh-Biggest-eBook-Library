import React from 'react';
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import Svg, { Circle, Line, Path, Rect } from 'react-native-svg';

import { useAppTheme } from '../context/ThemeContext';
import type { TabKey } from '../types';
import { BookOpenIcon, SettingsGearIcon } from './Icons';

interface Props {
  activeTab: TabKey;
  onSelectTab: (tab: TabKey) => void;
  bottomInset?: number;
}

function HomeIcon({ color }: { color: string }) {
  return (
    <Svg width={20} height={20} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={1.9}>
      <Path d="M3 10.5L12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1v-9.5z" />
    </Svg>
  );
}

function CategoriesGridIcon({ color }: { color: string }) {
  return (
    <Svg width={24} height={24} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={2}>
      <Rect x="3.5" y="3.5" width="7" height="7" rx="1.8" />
      <Rect x="13.5" y="3.5" width="7" height="7" rx="1.8" />
      <Rect x="3.5" y="13.5" width="7" height="7" rx="1.8" />
      <Rect x="13.5" y="13.5" width="7" height="7" rx="1.8" />
    </Svg>
  );
}

function StatsIcon({ color }: { color: string }) {
  return (
    <Svg width={20} height={20} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={1.9}>
      <Line x1="6" y1="20" x2="6" y2="10" />
      <Line x1="12" y1="20" x2="12" y2="4" />
      <Line x1="18" y1="20" x2="18" y2="14" />
    </Svg>
  );
}

function LibraryNavIcon({ color }: { color: string }) {
  return <BookOpenIcon size={20} color={color} />;
}

function SettingsNavIcon({ color }: { color: string }) {
  return <SettingsGearIcon size={20} color={color} />;
}

export function BottomNavBar({ activeTab, onSelectTab, bottomInset = 10 }: Props) {
  const { theme } = useAppTheme();

  const renderTab = (key: TabKey, label: string, Icon: React.ComponentType<{ color: string }>) => {
    const active = activeTab === key;
    const color = active ? theme.ink : theme.muted;
    return (
      <TouchableOpacity
        key={key}
        style={[
          styles.tabBtn,
          active && { backgroundColor: theme.surfaceAlt },
        ]}
        onPress={() => onSelectTab(key)}
        activeOpacity={0.75}
      >
        <Icon color={color} />
        <Text style={[styles.tabLabel, { color: active ? theme.ink : theme.muted }, active && styles.tabLabelActive]}>
          {label}
        </Text>
      </TouchableOpacity>
    );
  };

  const exploreActive = activeTab === 'explore';

  return (
    <View style={[styles.outerWrap, { paddingBottom: Math.max(bottomInset, 10) }]} pointerEvents="box-none">
      <View
        style={[
          styles.pillBar,
          {
            backgroundColor: theme.surfaceDeep,
            borderColor: theme.border,
          },
        ]}
      >
        {renderTab('home', 'Home', HomeIcon)}
        {renderTab('library', 'Library', LibraryNavIcon)}

        <TouchableOpacity
          style={styles.fabWrap}
          onPress={() => onSelectTab('explore')}
          activeOpacity={0.85}
          accessibilityLabel="Explore Categories"
        >
          <View
            style={[
              styles.fab,
              {
                backgroundColor: exploreActive ? theme.cream : theme.accent,
                borderColor: exploreActive ? theme.accent : theme.bg,
              },
            ]}
          >
            <CategoriesGridIcon color={theme.creamInk} />
          </View>
        </TouchableOpacity>

        {renderTab('stats', 'Stats', StatsIcon)}
        {renderTab('more', 'Settings', SettingsNavIcon)}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  outerWrap: {
    position: 'absolute',
    left: 16,
    right: 16,
    bottom: 0,
    alignItems: 'center',
  },
  pillBar: {
    width: '100%',
    height: 66,
    borderRadius: 34,
    borderWidth: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-around',
    paddingHorizontal: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 10 },
    shadowOpacity: 0.35,
    shadowRadius: 18,
    elevation: 16,
  },
  tabBtn: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 22,
    gap: 3,
  },
  tabLabel: {
    fontSize: 10,
    fontWeight: '600',
  },
  tabLabelActive: {
    fontWeight: '700',
  },
  fabWrap: {
    marginTop: -26,
    alignItems: 'center',
    justifyContent: 'center',
  },
  fab: {
    width: 56,
    height: 56,
    borderRadius: 28,
    borderWidth: 2,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.35,
    shadowRadius: 10,
    elevation: 10,
  },
});
