import React, { useState, useEffect, useRef } from 'react';
import { 
  StyleSheet, 
  Text, 
  View, 
  TextInput, 
  TouchableOpacity, 
  FlatList,
  SectionList,
  Image,
  ActivityIndicator,
  ScrollView,
  Platform,
  StatusBar,
  KeyboardAvoidingView,
  LayoutAnimation,
  UIManager
} from 'react-native';

// Enable LayoutAnimation for Android
if (Platform.OS === 'android' && UIManager.setLayoutAnimationEnabledExperimental) {
  UIManager.setLayoutAnimationEnabledExperimental(true);
}

import axios from 'axios';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';

// Base URL for the backend
const API_URL = process.env.EXPO_PUBLIC_API_URL || (Platform.OS === 'android' ? 'http://10.0.2.2:8000' : 'http://localhost:8000');

interface Photo {
  id: string;
  url: string;
  caption: string;
  metadata: any;
}

interface Suggestion {
  category: string;
  label: string;
  value: string;
}

interface ActiveConstraint {
  dimension: string;
  label: string;
  value: string;
  removable: boolean;
  source: string;
}

interface RecoveryOption {
  label: string;
  action: string;
  dimension: string | null;
  value: string | null;
}

const getTheme = (isDark: boolean) => ({
  bg: isDark ? '#131314' : '#FFFFFF',
  text: isDark ? '#E3E3E3' : '#1F1F1F',
  textMuted: isDark ? '#8E918F' : '#5F6368',
  surface: isDark ? '#2D2F31' : '#F1F3F4',
  surfaceBorder: isDark ? '#444746' : '#DADCE0',
  primary: isDark ? '#A8C7FA' : '#0B57D0',
  primarySurface: isDark ? '#3F484B' : '#D3E3FD',
  avatarBg: isDark ? '#8AB4F8' : '#1A73E8',
  avatarText: isDark ? '#131314' : '#FFFFFF',
  icon: isDark ? '#E3E3E3' : '#444746',
  dateBadgeBg: isDark ? '#1F1F1F' : '#FFFFFF',
  danger: isDark ? '#F28B82' : '#D93025',
  warning: isDark ? '#FDE293' : '#F9AB00',
});

const trackEvent = async (eventName: string, properties: any = {}) => {
  try {
    await axios.post(`${API_URL}/api/track`, {
      event_name: eventName,
      properties
    });
  } catch (e) {
    console.error("Analytics error:", e);
  }
};

export default function App() {
  const [view, setView] = useState<'home' | 'search'>('home');
  const [isDark, setIsDark] = useState(true);
  const theme = getTheme(isDark);
  
  // Search state
  const [query, setQuery] = useState('');
  const [userFacingQuery, setUserFacingQuery] = useState('');
  const [results, setResults] = useState<Photo[]>([]);
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [activeConstraints, setActiveConstraints] = useState<ActiveConstraint[]>([]);
  const [isRecoveryMode, setIsRecoveryMode] = useState(false);
  const [recoveryOptions, setRecoveryOptions] = useState<RecoveryOption[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [needsRefinement, setNeedsRefinement] = useState(false);
  const [suggestionIndex, setSuggestionIndex] = useState(0);
  const [refinementQuestion, setRefinementQuestion] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [showCustomInput, setShowCustomInput] = useState(false);
  const [customInputValue, setCustomInputValue] = useState('');

  const [homePhotos, setHomePhotos] = useState<Photo[]>([]);

  useEffect(() => {
    const fetchHomePhotos = async () => {
      try {
        const res = await axios.get(`${API_URL}/api/photos?limit=300`);
        setHomePhotos(res.data.results);
      } catch (e) {
        console.error("Error fetching home photos:", e);
      }
    };
    fetchHomePhotos();
  }, []);

  const getGroupedPhotos = () => {
    const sections: { title: string, data: Photo[][] }[] = [];
    if (homePhotos.length === 0) return sections;

    let currentDate = new Date('2025-09-11');
    let currentChunkIndex = 0;
    const CHUNK_SIZE = 16;

    while (currentChunkIndex < homePhotos.length) {
      const chunk = homePhotos.slice(currentChunkIndex, currentChunkIndex + CHUNK_SIZE);
      const rows: Photo[][] = [];
      for (let i = 0; i < chunk.length; i += 4) {
        rows.push(chunk.slice(i, i + 4));
      }
      
      const dateStr = currentDate.toLocaleDateString('en-US', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' });
      
      sections.push({
        title: dateStr,
        data: rows
      });

      currentDate.setDate(currentDate.getDate() - Math.floor(Math.random() * 3 + 1));
      currentChunkIndex += CHUNK_SIZE;
    }
    return sections;
  };

  // Abort controller ref for race condition handling (debouncing)
  const abortControllerRef = useRef<AbortController | null>(null);

  const animateLayout = () => {
    LayoutAnimation.configureNext(LayoutAnimation.Presets.easeInEaseOut);
  };

  const processSearchResponse = (data: any) => {
    animateLayout();
    setResults(data.results);
    setNeedsRefinement(data.needs_refinement);
    setSuggestions(data.suggestions || []);
    setSuggestionIndex(0);
    setRefinementQuestion(data.refinement_question || null);
    setSessionId(data.session_id);
    setUserFacingQuery(data.user_facing_query || query);
    if (data.user_facing_query) {
      setQuery(data.user_facing_query);
    }
    setActiveConstraints(data.active_constraints || []);
    setIsRecoveryMode(data.is_recovery_mode || false);
    setRecoveryOptions(data.recovery_options || []);
  };

  const handleSearch = async () => {
    setShowCustomInput(false);
    setCustomInputValue('');
    if (!query.trim()) return;
    
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();
    
    animateLayout();
    setLoading(true);
    setSearched(true);
    
    trackEvent('search_started', { query, session_id: sessionId });
    
    try {
      const response = await axios.get(`${API_URL}/api/search`, {
        params: { 
          q: query,
          session_id: sessionId 
        },
        signal: abortControllerRef.current.signal,
      });
      
      processSearchResponse(response.data);
      
      trackEvent('search_completed', { 
        query, 
        result_count: response.data.results.length,
        needs_refinement: response.data.needs_refinement,
        is_recovery_mode: response.data.is_recovery_mode
      });
    } catch (error) {
      if (!axios.isCancel(error)) {
        console.error("Search error:", error);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleRefine = async (action: string, dimension?: string, value?: string) => {
    if (!sessionId) return;
    
    if (action === 'custom' && value === 'custom') {
      setShowCustomInput(true);
      return;
    }
    
    setShowCustomInput(false);
    setCustomInputValue('');

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();

    animateLayout();
    setLoading(true);

    trackEvent('search_refined', { action, dimension, value, session_id: sessionId });

    try {
      const response = await axios.post(`${API_URL}/api/refine`, {
        session_id: sessionId,
        action,
        dimension,
        value
      }, {
        signal: abortControllerRef.current.signal,
      });

      processSearchResponse(response.data);

    } catch (error) {
      if (!axios.isCancel(error)) {
        console.error("Refine error:", error);
      }
    } finally {
      setLoading(false);
    }
  };

  const resetSearch = async () => {
    if (sessionId) {
      try {
        await axios.post(`${API_URL}/api/reset`, { session_id: sessionId });
      } catch(e) { console.error(e); }
    }
    animateLayout();
    setQuery('');
    setUserFacingQuery('');
    setResults([]);
    setSuggestions([]);
    setActiveConstraints([]);
    setSearched(false);
    setRefinementQuestion(null);
    setSessionId(null);
    setIsRecoveryMode(false);
    setRecoveryOptions([]);
  };

  const renderPhoto = ({ item, isHome = false }: { item: any, isHome?: boolean }) => {
    const id = item.id.replace('photo_', '');
    let url = item.url;
    
    // Properly encode filename to handle spaces and special characters like # and emojis
    try {
      if (url.startsWith('/static/images/')) {
        const filename = url.replace('/static/images/', '');
        url = `/static/images/${encodeURIComponent(filename)}`;
      }
      url = url.startsWith('/') ? `${API_URL}${url}` : url;
    } catch (e) {
      console.error("URL Encoding Error", e);
    }
    
    return (
      <TouchableOpacity 
        style={styles.photoContainer}
        onPress={() => {
          if (!isHome) {
            trackEvent('photo_click', { photo_id: id, query });
          }
        }}
        activeOpacity={0.8}
      >
        <Image 
          source={{ uri: url }} 
          style={[styles.photo, { backgroundColor: theme.surface }]} 
        />
      </TouchableOpacity>
    );
  }

  const renderRow = ({ item }: { item: Photo[] }) => {
    return (
      <View style={styles.photoRow}>
        {item.map(photo => (
          <React.Fragment key={photo.id}>
            {renderPhoto({ item: photo, isHome: true })}
          </React.Fragment>
        ))}
        {item.length < 4 && Array.from({ length: 4 - item.length }).map((_, i) => (
          <View key={`empty-${i}`} style={styles.photoContainer} />
        ))}
      </View>
    );
  }

  const renderHome = () => (
    <View style={styles.fullScreen}>
      <View style={styles.homeHeader}>
        <View style={[styles.backupBadge, { backgroundColor: theme.surface }]}>
          <Ionicons name="cloud-done-outline" size={16} color={theme.icon} />
          <Text style={[styles.backupText, { color: theme.text }]}>Backup complete</Text>
        </View>
        <View style={styles.headerIcons}>
          <TouchableOpacity onPress={() => setIsDark(!isDark)}>
            <Ionicons name={isDark ? "sunny" : "moon"} size={24} color={theme.icon} style={styles.iconSpaced} />
          </TouchableOpacity>
          <View style={[styles.avatar, { backgroundColor: theme.avatarBg }]}>
            <Text style={[styles.avatarText, { color: theme.avatarText }]}>T</Text>
          </View>
        </View>
      </View>

      <SectionList
        sections={getGroupedPhotos()}
        keyExtractor={(item, index) => index.toString()}
        renderItem={renderRow}
        renderSectionHeader={({ section: { title } }) => (
          <View style={styles.sectionHeaderContainer}>
             <Text style={[styles.sectionHeaderText, { color: theme.text }]}>{title}</Text>
          </View>
        )}
        stickySectionHeadersEnabled={false}
        contentContainerStyle={{ paddingBottom: 100 }}
      />

      <View style={styles.bottomNavContainer}>
        <View style={[styles.bottomNavPill, { backgroundColor: theme.surface }]}>
          <TouchableOpacity style={[styles.navItem, { backgroundColor: theme.primarySurface }]}>
            <Ionicons name="images" size={20} color={theme.primary} />
            <Text style={[styles.navTextSelected, { color: theme.primary }]}>Photos</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.navItem}>
            <Text style={[styles.navText, { color: theme.textMuted }]}>Collections</Text>
          </TouchableOpacity>
        </View>
        <TouchableOpacity style={[styles.searchFab, { backgroundColor: theme.surface }]} onPress={() => { animateLayout(); setView('search'); }}>
          <Ionicons name="sparkles" size={20} color={theme.primary} style={{ marginRight: 6 }} />
          <Ionicons name="search" size={24} color={theme.icon} />
        </TouchableOpacity>
      </View>
    </View>
  );

  const renderSearch = () => (
    <KeyboardAvoidingView style={styles.fullScreen} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      {/* Search Header */}
      <View style={styles.searchHeader}>
        <TouchableOpacity onPress={() => { animateLayout(); setView('home'); }} style={styles.backButton}>
          <Ionicons name="arrow-back" size={24} color={theme.icon} />
        </TouchableOpacity>
        {searched && (
          <Text style={[styles.queryText, { color: theme.text }]}>
            {userFacingQuery || query}
          </Text>
        )}
      </View>

      {/* Results Area */}
      <View style={styles.resultsArea}>
        {loading ? (
          <ActivityIndicator size="large" color={theme.primary} style={{marginTop: 40}} />
        ) : searched && results.length === 0 ? (
          <View style={styles.emptyState}>
            <Ionicons name="search-outline" size={64} color={theme.textMuted} style={{marginBottom: 16}} />
            <Text style={[styles.emptyText, { color: theme.text }]}>No photos match your search</Text>
            
            {isRecoveryMode && recoveryOptions.length > 0 && (
               <View style={styles.recoveryContainer}>
                 <Text style={[styles.emptySubText, { color: theme.textMuted, marginBottom: 16 }]}>
                   Your search might be too specific. Try broadening it:
                 </Text>
                 {showCustomInput ? (
                   <View style={{flexDirection: 'row', alignItems: 'center', width: '100%'}}>
                     <TextInput
                       style={[styles.recoveryBtn, { flex: 1, color: theme.text, backgroundColor: theme.surface, textAlign: 'left' }]}
                       placeholder="Describe what you're looking for..."
                       placeholderTextColor={theme.textMuted}
                       value={customInputValue}
                       onChangeText={setCustomInputValue}
                       autoFocus={true}
                       onSubmitEditing={() => {
                         if (customInputValue.trim()) {
                           handleRefine('custom', 'custom', customInputValue.trim());
                         } else {
                           setShowCustomInput(false);
                         }
                       }}
                       returnKeyType="search"
                     />
                     <TouchableOpacity onPress={() => setShowCustomInput(false)} style={{marginLeft: 8}}>
                       <Ionicons name="close-circle" size={24} color={theme.textMuted} />
                     </TouchableOpacity>
                   </View>
                 ) : (
                   recoveryOptions.map((opt, idx) => (
                     <TouchableOpacity 
                       key={idx}
                       style={[styles.recoveryBtn, { borderColor: theme.primary, backgroundColor: theme.primarySurface }]}
                       onPress={() => {
                         if (opt.action === 'custom') {
                           setShowCustomInput(true);
                         } else {
                           handleRefine(opt.action, opt.dimension || undefined, opt.value || undefined);
                         }
                       }}
                     >
                       <Text style={{color: theme.primary, fontWeight: '600'}}>{opt.label}</Text>
                     </TouchableOpacity>
                   ))
                 )}
               </View>
            )}
            {!isRecoveryMode && (
              <Text style={[styles.emptySubText, { color: theme.textMuted }]}>Try removing some filters or searching for something else.</Text>
            )}
          </View>
        ) : (
          <FlatList
            data={results}
            keyExtractor={(item) => item.id}
            numColumns={4}
            renderItem={({item}) => renderPhoto({item, isHome: false})}
          />
        )}
      </View>

      {/* Constraints & Suggestions Bottom Area */}
      <View style={styles.searchBottomContainer}>
        
        {/* Active Constraints */}
        {searched && activeConstraints.length > 0 && (
          <View style={styles.constraintsContainer}>
            <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.chipScroll}>
              {activeConstraints.map((constraint, idx) => (
                <TouchableOpacity 
                  key={`ac-${idx}`} 
                  style={[styles.constraintChip, { backgroundColor: theme.surface, borderColor: theme.surfaceBorder }]} 
                  onPress={() => handleRefine('remove', constraint.dimension, constraint.value)}
                >
                  <Text style={[styles.constraintChipText, { color: theme.text }]}>{constraint.label}</Text>
                  <Ionicons name="close-circle" size={16} color={theme.textMuted} style={{marginLeft: 6}} />
                </TouchableOpacity>
              ))}
            </ScrollView>
          </View>
        )}

        {/* Smart Suggestions */}
        {searched && needsRefinement && !isRecoveryMode && suggestions.length > 0 && (
          <View style={styles.suggestionsContainer}>
            <Text style={[styles.suggestionTitle, { color: theme.primary }]}>{refinementQuestion || 'Help us narrow it down:'}</Text>
            {showCustomInput ? (
              <View style={{flexDirection: 'row', alignItems: 'center', paddingHorizontal: 16}}>
                <TextInput
                  style={[styles.chip, { flex: 1, color: theme.text, backgroundColor: theme.surface }]}
                  placeholder="Describe what you're looking for..."
                  placeholderTextColor={theme.textMuted}
                  value={customInputValue}
                  onChangeText={setCustomInputValue}
                  autoFocus={true}
                  onSubmitEditing={() => {
                    if (customInputValue.trim()) {
                      handleRefine('custom', 'custom', customInputValue.trim());
                    } else {
                      setShowCustomInput(false);
                    }
                  }}
                  returnKeyType="search"
                />
                <TouchableOpacity onPress={() => setShowCustomInput(false)} style={{marginLeft: 8}}>
                  <Ionicons name="close-circle" size={24} color={theme.textMuted} />
                </TouchableOpacity>
              </View>
            ) : (
              <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.chipScroll}>
                {suggestions.map((s, i) => (
                  <TouchableOpacity 
                    key={`sug-${i}`} 
                    style={[styles.chip, { backgroundColor: theme.bg, borderColor: theme.surfaceBorder }]} 
                    onPress={() => {
                      if (s.value === '__not_sure__') {
                        handleRefine('not_sure', s.category);
                      } else {
                        handleRefine(s.category === 'custom' ? 'custom' : 'add', s.category, s.value);
                      }
                    }}
                  >
                    <Text style={[styles.chipText, { color: s.value === '__not_sure__' ? theme.textMuted : theme.text }]}>
                      {s.value === '__not_sure__' ? s.label : s.category === 'custom' ? s.label : `+ ${s.label}`}
                    </Text>
                  </TouchableOpacity>
                ))}
              </ScrollView>
            )}
          </View>
        )}

        {/* Search Bar */}
        <View style={[styles.floatingSearchBar, { backgroundColor: theme.surface }]}>
          <TextInput
            style={[styles.searchInput, { color: theme.text }]}
            placeholder="Search for your photos"
            placeholderTextColor={theme.textMuted}
            value={query}
            onChangeText={setQuery}
            onSubmitEditing={() => {
               // When typing a new query entirely, we clear session to start fresh
               if (query !== userFacingQuery) {
                 setSessionId(null);
               }
               handleSearch();
            }}
            returnKeyType="search"
            autoFocus={!searched}
          />
          {query.length > 0 ? (
             <TouchableOpacity onPress={resetSearch}>
               <Ionicons name="close" size={24} color={theme.icon} />
             </TouchableOpacity>
          ) : (
             <Ionicons name="mic-outline" size={24} color={theme.icon} />
          )}
        </View>
      </View>
    </KeyboardAvoidingView>
  );

  return (
    <SafeAreaView style={[styles.safeArea, { backgroundColor: theme.bg }]} edges={['top', 'bottom']}>
      <StatusBar barStyle={isDark ? "light-content" : "dark-content"} backgroundColor={theme.bg} />
      {view === 'home' ? renderHome() : renderSearch()}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1 },
  fullScreen: { flex: 1 },
  homeHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: 16, paddingVertical: 12 },
  backupBadge: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 12, paddingVertical: 8, borderRadius: 20 },
  backupText: { marginLeft: 8, fontSize: 14, fontWeight: '500' },
  headerIcons: { flexDirection: 'row', alignItems: 'center' },
  iconSpaced: { marginHorizontal: 10 },
  avatar: { width: 32, height: 32, borderRadius: 16, justifyContent: 'center', alignItems: 'center', marginLeft: 8 },
  avatarText: { fontWeight: 'bold', fontSize: 16 },
  dateHeaderContainer: { alignItems: 'center', marginVertical: 16, position: 'absolute', top: 10, left: 0, right: 0, zIndex: 10 },
  dateBadge: { paddingHorizontal: 16, paddingVertical: 6, borderRadius: 16, opacity: 0.9, elevation: 2 },
  dateText: { fontSize: 12, fontWeight: '600' },
  bottomNavContainer: { position: 'absolute', bottom: 20, left: 16, right: 16, flexDirection: 'row', justifyContent: 'center', alignItems: 'center' },
  bottomNavPill: { flexDirection: 'row', borderRadius: 30, padding: 6, marginRight: 10 },
  navItem: { flexDirection: 'row', alignItems: 'center', paddingVertical: 10, paddingHorizontal: 16, borderRadius: 24 },
  navText: { fontSize: 14, fontWeight: '600' },
  navTextSelected: { fontSize: 14, fontWeight: '600', marginLeft: 6 },
  searchFab: { height: 56, borderRadius: 28, flexDirection: 'row', justifyContent: 'center', alignItems: 'center', paddingHorizontal: 20, elevation: 4, shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.25, shadowRadius: 3.84 },
  photoContainer: { flex: 1/4, aspectRatio: 1, padding: 1 },
  photoRow: { flexDirection: 'row', width: '100%' },
  sectionHeaderContainer: { paddingHorizontal: 16, paddingVertical: 12 },
  sectionHeaderText: { fontSize: 14, fontWeight: '600' },
  photo: { flex: 1 },
  searchHeader: { paddingHorizontal: 16, paddingVertical: 12, flexDirection: 'row', alignItems: 'center' },
  backButton: { padding: 8, marginLeft: -8, marginRight: 8 },
  queryText: { fontSize: 18, fontWeight: '600', flex: 1 },
  resultsArea: { flex: 1 },
  emptyState: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 32 },
  emptyText: { fontSize: 18, fontWeight: '600', textAlign: 'center', marginBottom: 8 },
  emptySubText: { fontSize: 14, textAlign: 'center' },
  recoveryContainer: { marginTop: 24, width: '100%', alignItems: 'center' },
  recoveryBtn: { borderWidth: 1, borderRadius: 20, paddingVertical: 10, paddingHorizontal: 20, marginVertical: 6, width: '100%', alignItems: 'center' },
  searchBottomContainer: { paddingHorizontal: 16, paddingBottom: 20, paddingTop: 10, backgroundColor: 'transparent' },
  constraintsContainer: { marginBottom: 12 },
  constraintChip: { flexDirection: 'row', alignItems: 'center', borderWidth: 1, borderRadius: 20, paddingVertical: 6, paddingHorizontal: 12, marginRight: 8 },
  constraintChipText: { fontSize: 13, fontWeight: '500' },
  suggestionsContainer: { marginBottom: 12 },
  suggestionTitle: { fontSize: 14, fontWeight: '500', marginBottom: 10, marginLeft: 4 },
  chipScroll: { flexDirection: 'row' },
  chip: { borderWidth: 1, borderRadius: 20, paddingVertical: 8, paddingHorizontal: 16, marginRight: 8 },
  chipText: { fontSize: 14 },
  floatingSearchBar: { flexDirection: 'row', alignItems: 'center', borderRadius: 30, paddingHorizontal: 20, paddingVertical: 14, elevation: 4, shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.1, shadowRadius: 4 },
  searchInput: { flex: 1, fontSize: 16, padding: 0 }
});
