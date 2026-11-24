import React from 'react';
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import Svg, { Circle, Line, Path, Rect } from 'react-native-svg';

import { useAppTheme } from '../context/ThemeContext';
import type { TabKey } from '../types';

interface Props {
  activeTab: TabKey;
  onSelectTab: (tab: TabKey) => void;
  bottomInset?: number;
}

interface TabIconProps {
  color: string;
  active: boolean;
}

function HomeIcon({ color, active }: TabIconProps) {
  return (
    <Svg
      width={22}
      height={22}
      viewBox="0 0 24 24"
      fill={active ? color : 'none'}
      fillOpacity={active ? 0.22 : 0}
      stroke={color}
      strokeWidth={active ? 2.5 : 2.15}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <Path d="M3 10.5L12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1v-9.5z" />
    </Svg>
  );
}

function LibraryNavIcon({ color, active }: TabIconProps) {
  return (
    <Svg
      width={22}
      height={22}
      viewBox="0 0 24 24"
      fill={active ? color : 'none'}
      fillOpacity={active ? 0.28 : 0}
      stroke={color}
      strokeWidth={active ? 2.5 : 2.15}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <Path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" />
    </Svg>
  );
}

function ExploreGridIcon({ color, active }: TabIconProps) {
  return (
    <Svg
      width={22}
      height={22}
      viewBox="0 0 24 24"
      fill={active ? color : 'none'}
      fillOpacity={active ? 0.24 : 0}
      stroke={color}
      strokeWidth={active ? 2.5 : 2.15}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <Rect x="3.5" y="3.5" width="7" height="7" rx="1.8" />
      <Rect x="13.5" y="3.5" width="7" height="7" rx="1.8" />
      <Rect x="3.5" y="13.5" width="7" height="7" rx="1.8" />
      <Rect x="13.5" y="13.5" width="7" height="7" rx="1.8" />
    </Svg>
  );
}

function SearchNavIcon({ color, active }: TabIconProps) {
  return (
    <Svg
      width={22}
      height={22}
      viewBox="0 0 24 24"
      fill={active ? color : 'none'}
      fillOpacity={active ? 0.18 : 0}
      stroke={color}
      strokeWidth={active ? 2.65 : 2.2}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <Circle cx="10.5" cy="10.5" r="7" />
      <Line x1="21" y1="21" x2="15.6" y2="15.6" />
    </Svg>
  );
}

function SettingsNavIcon({ color, active }: TabIconProps) {
  return (
    <Svg
      width={22}
      height={22}
      viewBox="0 0 24 24"
      fill={active ? color : 'none'}
      fillOpacity={active ? 0.2 : 0}
      stroke={color}
      strokeWidth={active ? 2.45 : 2.1}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <Circle cx="12" cy="12" r="3" />
      <Path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </Svg>
  );
}

const TABS: {
  key: TabKey;
  label: string;
  Icon: React.ComponentType<TabIconProps>;
}[] = [
  { key: 'home', label: 'Home', Icon: HomeIcon },
  { key: 'library', label: 'Shelf', Icon: LibraryNavIcon },
  { key: 'explore', label: 'Explore', Icon: ExploreGridIcon },
  { key: 'search', label: 'Search', Icon: SearchNavIcon },
  { key: 'more', label: 'Settings', Icon: SettingsNavIcon },
];

export function BottomNavBar({ activeTab, onSelectTab, bottomInset = 10 }: Props) {
  const { theme } = useAppTheme();

  return (
    <View
      style={[styles.outerWrap, { paddingBottom: Math.max(bottomInset, 10) }]}
      pointerEvents="box-none"
    >
      <View
        style={[
          styles.dockBar,
          {
            backgroundColor: theme.surfaceDeep,
            borderColor: theme.border,
          },
        ]}
      >
        {TABS.map(({ key, label, Icon }) => {
          const active = activeTab === key;
          const iconColor = active ? theme.creamInk : theme.muted;

          return (
            <TouchableOpacity
              key={key}
              style={styles.tabBtn}
              onPress={() => onSelectTab(key)}
              activeOpacity={0.78}
              accessibilityRole="tab"
              accessibilityState={{ selected: active }}
              accessibilityLabel={label}
            >
              <View
                style={[
                  styles.indicatorCapsule,
                  active && [
                    styles.indicatorCapsuleActive,
                    { backgroundColor: theme.accent, borderColor: theme.cream },
                  ],
                ]}
              >
                <Icon color={iconColor} active={active} />
              </View>
              <Text
                style={[
                  styles.tabLabel,
                  { color: active ? theme.ink : theme.muted },
                  active && styles.tabLabelActive,
                ]}
                numberOfLines={1}
              >
                {label}
              </Text>
            </TouchableOpacity>
          );
        })}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  outerWrap: {
    position: 'absolute',
    left: 10,
    right: 10,
    bottom: 0,
    alignItems: 'center',
  },
  dockBar: {
    width: '100%',
    height: 74,
    borderRadius: 26,
    borderWidth: 2,
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 6,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 10 },
    shadowOpacity: 0.38,
    shadowRadius: 22,
    elevation: 18,
  },
  tabBtn: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 5,
    gap: 4,
  },
  indicatorCapsule: {
    width: 54,
    height: 34,
    borderRadius: 17,
    alignItems: 'center',
    justifyContent: 'center',
  },
  indicatorCapsuleActive: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.28,
    shadowRadius: 6,
    elevation: 5,
  },
  tabLabel: {
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 0.2,
  },
  tabLabelActive: {
    fontSize: 11.5,
    fontWeight: '800',
  },
});
