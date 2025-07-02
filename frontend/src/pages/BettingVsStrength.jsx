import React, { useState, useEffect, useMemo, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  Grid,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  CircularProgress,
  Alert,
  Divider,
  List,
  ListItem,
  ListItemText,
  ListItemButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Card,
  CardContent,
  Stack,
  alpha,
  Skeleton,
  IconButton,
  Tooltip,
} from '@mui/material'
import { 
  ScatterChart, 
  Scatter, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip as RechartsTooltip, 
  ResponsiveContainer,
  Legend,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  Cell,
} from 'recharts'
import { 
  TrendingUp as AnalysisIcon, 
  Person as PersonIcon,
  Casino as PokerIcon,
  History as HistoryIcon,
  Visibility as ViewIcon,
  Shield as ShieldIcon,
  Warning as WarningIcon,
  Info as InfoIcon,
  Refresh as RefreshIcon,
  ZoomIn as ZoomInIcon,
  ZoomOut as ZoomOutIcon,
} from '@mui/icons-material'
import { motion, AnimatePresence } from 'framer-motion'
import CountUp from 'react-countup'
import { FixedSizeList } from 'react-window'
import axios from 'axios'
import HandHistoryViewer from '../components/HandHistoryViewer'

// Enhanced color palettes
const STREET_COLORS = {
  'flop': '#00d4ff',
  'turn': '#ffa502',  
  'river': '#00ff88',
  'preflop': '#ff6b81'
}

const ACTION_COLORS = {
  'bet': '#00d4ff',
  '2bet': '#ff4757',
  '3bet': '#ff6b81',
  'checkraise': '#a55eea',
  'donk': '#795548',
  'probe': '#607D8B',
  'lead': '#26de81',
  'cont': '#45aaf2'
}

// Animation variants
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1
    }
  }
}

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { 
    opacity: 1, 
    y: 0,
    transition: {
      duration: 0.4
    }
  }
}

// Enhanced stat card component
function MetricCard({ title, value, icon, color, subtitle, trend, delay = 0 }) {
  const [isHovered, setIsHovered] = useState(false)
  
  return (
    <motion.div
      initial="hidden"
      animate="visible"
      variants={itemVariants}
      transition={{ delay }}
      whileHover={{ scale: 1.02 }}
      onHoverStart={() => setIsHovered(true)}
      onHoverEnd={() => setIsHovered(false)}
    >
      <Card
        sx={{
          background: 'linear-gradient(135deg, rgba(17, 24, 39, 0.9) 0%, rgba(17, 24, 39, 0.7) 100%)',
          backdropFilter: 'blur(10px)',
          border: '1px solid rgba(255, 255, 255, 0.05)',
          boxShadow: isHovered ? '0 8px 32px rgba(0, 212, 255, 0.2)' : '0 4px 24px rgba(0, 0, 0, 0.1)',
          transition: 'all 0.3s ease',
          height: '100%',
        }}
      >
        <CardContent>
          <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
            <Box
              sx={{
                p: 1.5,
                borderRadius: 2,
                background: alpha(color || '#00d4ff', 0.1),
                color: color || '#00d4ff',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              {icon}
            </Box>
            {trend && (
              <Chip
                size="small"
                label={trend}
                sx={{
                  backgroundColor: alpha(trend > 0 ? '#00ff88' : '#ff4757', 0.2),
                  color: trend > 0 ? '#00ff88' : '#ff4757',
                  fontWeight: 600,
                }}
              />
            )}
          </Box>
          <Typography variant="h5" sx={{ fontWeight: 700, mb: 0.5 }}>
            {typeof value === 'number' ? (
              <CountUp end={value} duration={2} separator="," decimals={0} />
            ) : (
              value
            )}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {title}
          </Typography>
          {subtitle && (
            <Typography variant="caption" sx={{ color: color || '#00d4ff', mt: 1, display: 'block' }}>
              {subtitle}
            </Typography>
          )}
        </CardContent>
      </Card>
    </motion.div>
  )
}

function BettingVsStrength() {
  const [urlSearchParams] = useSearchParams()
  const playerFromUrl = urlSearchParams.get('player') || ''
  
  const [filters, setFilters] = useState({
    player: playerFromUrl,
    streets: ['flop', 'turn', 'river'],
    actions: ['bet', '2bet', '3bet', 'checkraise', 'donk', 'probe', 'lead', 'cont'],
    limit: 1000
  })
  
  // Main data states
  const [data, setData] = useState([])
  const [summary, setSummary] = useState({})
  const [topOpponents, setTopOpponents] = useState([])
  const [playerIntentions, setPlayerIntentions] = useState([])
  const [recentHands, setRecentHands] = useState([])
  const [detailedStats, setDetailedStats] = useState({})
  
  // Loading states
  const [loading, setLoading] = useState(false)
  const [loadingHands, setLoadingHands] = useState(false)
  const [loadingStats, setLoadingStats] = useState(false)
  
  // UI states
  const [error, setError] = useState('')
  const [hasSearched, setHasSearched] = useState(false)
  const [colorBy, setColorBy] = useState('street') // 'street' or 'action'
  const [selectedStreet, setSelectedStreet] = useState('all') // 'all', 'preflop', 'flop', 'turn', 'river'
  const [selectedHandId, setSelectedHandId] = useState(null)
  const [showHandViewer, setShowHandViewer] = useState(false)

  // Auto-load data when component loads
  useEffect(() => {
    handleSearch()
    if (filters.player) {
      loadRecentHands()
      loadDetailedStats()
    }
  }, [])

  // Auto-search when player changes
  useEffect(() => {
    if (playerFromUrl !== filters.player) {
      setFilters(prev => ({ ...prev, player: playerFromUrl }))
      handleSearch()
      if (playerFromUrl) {
        loadRecentHands()
        loadDetailedStats()
      }
    }
  }, [playerFromUrl])

  const handleSearch = async () => {
    setLoading(true)
    setError('')
    setHasSearched(true)
    
    try {
      const response = await axios.get('/api/betting-vs-strength', {
        params: {
          player: filters.player,
          streets: filters.streets.join(','),
          actions: filters.actions.join(','),
          limit: filters.limit
        }
      })
      
      if (response.data.success) {
        setData(response.data.data || [])
        setSummary(response.data.summary || {})
        setTopOpponents(response.data.top_opponents || [])
        setPlayerIntentions(response.data.player_intentions || [])
      } else {
        setError(response.data.error || 'Failed to fetch data')
      }
    } catch (err) {
      setError('Could not fetch betting vs strength data')
      console.error('Search error:', err)
    } finally {
      setLoading(false)
    }
  }

  const loadRecentHands = async () => {
    if (!filters.player) return
    
    setLoadingHands(true)
    try {
      const response = await axios.get('/api/player-recent-hands', {
        params: { player_id: filters.player, limit: 20 }
      })
      
      if (response.data.success) {
        setRecentHands(response.data.data || [])
      }
    } catch (err) {
      console.error('Error loading recent hands:', err)
    } finally {
      setLoadingHands(false)
    }
  }

  const loadDetailedStats = async () => {
    if (!filters.player) return
    
    setLoadingStats(true)
    try {
      const response = await axios.get('/api/player-detailed-stats-comprehensive', {
        params: { player_id: filters.player }
      })
      
      if (response.data.success) {
        setDetailedStats(response.data.data || {})
      }
    } catch (err) {
      console.error('Error loading detailed stats:', err)
    } finally {
      setLoadingStats(false)
    }
  }

  const handleFilterChange = (filterName) => (event) => {
    setFilters({
      ...filters,
      [filterName]: event.target.value
    })
  }

  const handleChartClick = (data) => {
    if (data && data.activePayload && data.activePayload[0]) {
      const point = data.activePayload[0].payload
      if (point.hand_id) {
        setSelectedHandId(point.hand_id)
        setShowHandViewer(true)
      }
    }
  }

  const handleIntentionClick = (intention) => {
    // Filter data to show only this intention
    const filteredIntentionData = data.filter(point => 
      point.intention === intention.intention
    )
    console.log('Filtering by intention:', intention.intention, filteredIntentionData)
    // You could set a filter state here to highlight these points
  }

  const handleHandClick = (handId) => {
    setSelectedHandId(handId)
    setShowHandViewer(true)
  }

  // Filter data by selected street
  const filteredData = selectedStreet === 'all' 
    ? data 
    : data.filter(point => point.street === selectedStreet)

  // Format data for Recharts
  const chartData = filteredData.map(point => ({
    ...point,
    x: point.hand_strength,
    y: point.bet_size_pct,
    fill: colorBy === 'street' ? STREET_COLORS[point.street] : ACTION_COLORS[point.action_label]
  }))

  // Custom tooltip for scatter plot
  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload
      return (
        <Paper sx={{ p: 2, maxWidth: 300, cursor: 'pointer' }}>
          <Typography variant="subtitle2" gutterBottom>
            {data.nickname || data.player_id}
          </Typography>
          <Typography variant="body2">
            <strong>Hand Strength:</strong> {data.hand_strength}
          </Typography>
          <Typography variant="body2">
            <strong>Bet Size:</strong> {data.bet_size_pct}% of pot
          </Typography>
          <Typography variant="body2">
            <strong>Street:</strong> {data.street}
          </Typography>
          <Typography variant="body2">
            <strong>Action:</strong> {data.action_label}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Hand: {data.hand_id}
          </Typography>
          <Typography variant="caption" color="primary">
            Click to view hand details
          </Typography>
        </Paper>
      )
    }
    return null
  }

  // Custom tooltip for radar chart
  const RadarTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload
      return (
        <Paper sx={{ p: 2, maxWidth: 250, cursor: 'pointer' }}>
          <Typography variant="subtitle2" gutterBottom>
            {label}
          </Typography>
          <Typography variant="body2">
            <strong>Frequency:</strong> {data.frequency_pct}%
          </Typography>
          <Typography variant="body2">
            <strong>Count:</strong> {data.n_actions} actions
          </Typography>
          <Typography variant="body2">
            <strong>Avg J-Score:</strong> {data.avg_j_score}
          </Typography>
          <Typography variant="caption" color="primary">
            Click to filter by intention
          </Typography>
        </Paper>
      )
    }
    return null
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Betting Size vs Hand Strength Analysis
      </Typography>
      <Typography variant="subtitle1" color="text.secondary" gutterBottom>
        Comprehensive poker analysis with betting patterns, player stats, and hand history
      </Typography>

      {/* Player Information Section */}
      {filters.player && (
        <Paper sx={{ p: 3, mt: 3, mb: 3, backgroundColor: '#f8f9fa', border: '1px solid #e0e0e0' }}>
          <Box display="flex" alignItems="center" gap={2}>
            <PersonIcon color="primary" sx={{ fontSize: 32 }} />
            <Box>
              <Typography variant="h5" color="primary">
                {filters.player}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Complete analysis with betting patterns, stats, and hand history
              </Typography>
            </Box>
          </Box>
        </Paper>
      )}

      {/* Compact Filters Section */}
      <Paper sx={{ p: 2, mt: 2 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} md={3}>
            <TextField
              fullWidth
              label="Player"
              variant="outlined"
              size="small"
              value={filters.player}
              onChange={handleFilterChange('player')}
              placeholder="Enter player name"
            />
          </Grid>
          
          <Grid item xs={12} md={2}>
            <FormControl fullWidth size="small">
              <InputLabel>Color By</InputLabel>
              <Select
                value={colorBy}
                onChange={(e) => setColorBy(e.target.value)}
                label="Color By"
              >
                <MenuItem value="street">Street</MenuItem>
                <MenuItem value="action">Action</MenuItem>
              </Select>
            </FormControl>
          </Grid>

          <Grid item xs={12} md={2}>
            <TextField
              fullWidth
              type="number"
              label="Limit"
              variant="outlined"
              size="small"
              value={filters.limit}
              onChange={handleFilterChange('limit')}
              inputProps={{ min: 100, max: 5000, step: 100 }}
            />
          </Grid>
          
          <Grid item xs={12} md={3}>
            <Button
              variant="contained"
              startIcon={<AnalysisIcon />}
              onClick={handleSearch}
              disabled={loading}
              size="small"
            >
              {loading ? 'Updating...' : 'Update Analysis'}
            </Button>
          </Grid>
        </Grid>
      </Paper>

      {error && (
        <Alert severity="error" sx={{ mt: 3 }}>
          {error}
        </Alert>
      )}

      {loading && (
        <Box display="flex" justifyContent="center" sx={{ mt: 4 }}>
          <CircularProgress />
        </Box>
      )}

      {/* Results Section - New 3-column layout */}
      {!loading && data.length > 0 && (
        <Box sx={{ mt: 3 }}>
          <Grid container spacing={2}>
            {/* Left Column - Opponents & Stats (25%) */}
            <Grid item xs={12} md={3}>
              {/* Top Opponents */}
              {filters.player && topOpponents.length > 0 && (
                <Paper sx={{ p: 2, mb: 2 }}>
                  <Typography variant="h6" gutterBottom>
                    Top Opponents
                  </Typography>
                  {topOpponents.map((opponent, index) => (
                    <Box key={opponent.player_id} sx={{ mb: 1, p: 1.5, backgroundColor: '#f5f5f5', borderRadius: 1 }}>
                      <Typography variant="subtitle2" color="primary">
                        #{index + 1} {opponent.nickname || opponent.player_id}
                      </Typography>
                      <Typography variant="caption" display="block">
                        {opponent.hands_together} hands
                      </Typography>
                      <Typography variant="caption" display="block">
                        You {opponent.player_avg_score} vs {opponent.opponent_avg_score}
                      </Typography>
                      <Typography variant="caption" color={opponent.score_diff > 0 ? 'success.main' : 'error.main'}>
                        {opponent.score_diff > 0 ? '+' : ''}{opponent.score_diff}
                      </Typography>
                    </Box>
                  ))}
                </Paper>
              )}

              {/* Summary Stats */}
              <Paper sx={{ p: 2, mb: 2 }}>
                <Typography variant="h6" gutterBottom>
                  Summary
                </Typography>
                <Grid container spacing={1}>
                  <Grid item xs={6}>
                    <Typography variant="h6" color="primary">
                      {filteredData.length}
                    </Typography>
                    <Typography variant="caption">Data Points</Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="h6" color="primary">
                      {selectedStreet === 'all' ? 'All' : selectedStreet.charAt(0).toUpperCase() + selectedStreet.slice(1)}
                    </Typography>
                    <Typography variant="caption">Street Filter</Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="h6" color="primary">
                      {Math.round(summary.bet_size_range?.max || 150)}%
                    </Typography>
                    <Typography variant="caption">Max Bet Size</Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="h6" color="primary">
                      {summary.hand_strength_range?.max || 100}
                    </Typography>
                    <Typography variant="caption">Max Strength</Typography>
                  </Grid>
                </Grid>
              </Paper>

              {/* Detailed Player Stats */}
              {filters.player && detailedStats && Object.keys(detailedStats).length > 0 && (
                <Paper sx={{ p: 2, mb: 2 }}>
                  <Typography variant="h6" gutterBottom>
                    Player Stats
                  </Typography>
                  {loadingStats ? (
                    <CircularProgress size={24} />
                  ) : (
                    <Box>
                      <Grid container spacing={1}>
                        <Grid item xs={6}>
                          <Typography variant="body2" color="primary">
                            {detailedStats.vpip}%
                          </Typography>
                          <Typography variant="caption">VPIP</Typography>
                        </Grid>
                        <Grid item xs={6}>
                          <Typography variant="body2" color="primary">
                            {detailedStats.pfr}%
                          </Typography>
                          <Typography variant="caption">PFR</Typography>
                        </Grid>
                        <Grid item xs={6}>
                          <Typography variant="body2" color="primary">
                            {detailedStats.aggression_factor}
                          </Typography>
                          <Typography variant="caption">Agg Factor</Typography>
                        </Grid>
                        <Grid item xs={6}>
                          <Typography variant="body2" color="primary">
                            {detailedStats.overall_score}
                          </Typography>
                          <Typography variant="caption">Avg J-Score</Typography>
                        </Grid>
                        <Grid item xs={12}>
                          <Typography variant="caption" color="text.secondary">
                            {detailedStats.total_hands} hands • {detailedStats.total_actions} actions
                          </Typography>
                        </Grid>
                      </Grid>
                    </Box>
                  )}
                </Paper>
              )}

              {/* Recent Hands */}
              {filters.player && (
                <Paper sx={{ p: 2 }}>
                  <Typography variant="h6" gutterBottom>
                    <HistoryIcon sx={{ mr: 1, fontSize: 18 }} />
                    Recent Hands (20)
                  </Typography>
                  {loadingHands ? (
                    <CircularProgress size={24} />
                  ) : recentHands.length > 0 ? (
                    <List dense sx={{ maxHeight: 300, overflowY: 'auto' }}>
                      {recentHands.map((hand, index) => (
                        <ListItem key={hand.hand_id} disablePadding>
                          <ListItemButton 
                            onClick={() => handleHandClick(hand.hand_id)}
                            sx={{ py: 0.5 }}
                          >
                            <ListItemText
                              primary={
                                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                  <Typography variant="body2">
                                    {hand.position} • {hand.holecards || '??'}
                                  </Typography>
                                  <Chip 
                                    label={hand.pot_type} 
                                    size="small" 
                                    variant="outlined"
                                    color={hand.money_won >= 0 ? 'success' : 'error'}
                                  />
                                </Box>
                              }
                              secondary={
                                <Typography variant="caption" color="text.secondary">
                                  {hand.money_won >= 0 ? '+' : ''}{hand.money_won}bb • J-Score: {hand.avg_j_score}
                                </Typography>
                              }
                            />
                            <ViewIcon fontSize="small" />
                          </ListItemButton>
                        </ListItem>
                      ))}
                    </List>
                  ) : (
                    <Typography variant="body2" color="text.secondary">
                      No recent hands available
                    </Typography>
                  )}
                </Paper>
              )}
            </Grid>

            {/* Middle Column - Scatter Chart (42%) */}
            <Grid item xs={12} md={5}>
              <Paper sx={{ p: 2 }}>
                {/* Street Filter Buttons */}
                <Box sx={{ mb: 2, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                  {['all', 'preflop', 'flop', 'turn', 'river'].map((street) => (
                    <Button
                      key={street}
                      variant={selectedStreet === street ? 'contained' : 'outlined'}
                      size="small"
                      onClick={() => setSelectedStreet(street)}
                      sx={{ minWidth: 80 }}
                    >
                      {street === 'all' ? 'All Streets' : street.charAt(0).toUpperCase() + street.slice(1)}
                    </Button>
                  ))}
                </Box>

                <Typography variant="h6" gutterBottom>
                  Betting Size vs Hand Strength
                </Typography>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  X: Hand Strength (1-100) | Y: Bet Size (% pot) | Colors: {colorBy === 'street' ? 'Streets' : 'Actions'}
                  {selectedStreet !== 'all' && ` | Showing: ${selectedStreet}`}
                </Typography>
                
                <Box sx={{ width: '100%', height: 400, mt: 1 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <ScatterChart 
                      margin={{ top: 10, right: 20, bottom: 30, left: 20 }}
                      onClick={handleChartClick}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                      <XAxis 
                        type="number" 
                        dataKey="x" 
                        name="Hand Strength" 
                        domain={[0, 100]}
                        label={{ value: 'Hand Strength', position: 'insideBottom', offset: -15 }}
                        tick={{ fontSize: 12 }}
                      />
                      <YAxis 
                        type="number" 
                        dataKey="y" 
                        name="Bet Size %" 
                        domain={[0, 150]}
                        label={{ value: 'Bet Size (%)', angle: -90, position: 'insideLeft' }}
                        tick={{ fontSize: 12 }}
                      />
                      <RechartsTooltip content={<CustomTooltip />} />
                      <Scatter data={chartData} />
                    </ScatterChart>
                  </ResponsiveContainer>
                </Box>
                
                {/* Legend */}
                <Box sx={{ mt: 1, display: 'flex', flexWrap: 'wrap', gap: 1, justifyContent: 'center' }}>
                  {colorBy === 'street' ? (
                    Object.entries(STREET_COLORS).map(([street, color]) => (
                      (selectedStreet === 'all' || selectedStreet === street) && (
                        <Box key={street} sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                          <Box sx={{ width: 12, height: 12, backgroundColor: color, borderRadius: '50%' }} />
                          <Typography variant="caption">{street}</Typography>
                        </Box>
                      )
                    ))
                  ) : (
                    Object.entries(ACTION_COLORS).map(([action, color]) => (
                      <Box key={action} sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                        <Box sx={{ width: 12, height: 12, backgroundColor: color, borderRadius: '50%' }} />
                        <Typography variant="caption">{action}</Typography>
                      </Box>
                    ))
                  )}
                </Box>
              </Paper>
            </Grid>

            {/* Right Column - Radar Chart (33%) */}
            <Grid item xs={12} md={4}>
              {filters.player && playerIntentions.length > 0 ? (
                <Paper sx={{ p: 2 }}>
                  <Typography variant="h6" gutterBottom>
                    Player Intentions Radar
                  </Typography>
                  <Typography variant="caption" color="text.secondary" gutterBottom display="block">
                    Top 10 most frequent play intentions
                  </Typography>
                  
                  <Box sx={{ width: '100%', height: 400, mt: 2 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <RadarChart 
                        data={playerIntentions} 
                        margin={{ top: 20, right: 20, bottom: 20, left: 20 }}
                        onClick={(data) => data && data.payload && handleIntentionClick(data.payload)}
                      >
                        <PolarGrid gridType="polygon" />
                        <PolarAngleAxis 
                          dataKey="intention" 
                          tick={{ fontSize: 9, fill: '#666' }}
                          className="radar-angle-axis"
                        />
                        <PolarRadiusAxis 
                          angle={90} 
                          domain={[0, 100]} 
                          tick={{ fontSize: 8, fill: '#999' }}
                          tickCount={5}
                        />
                        <Radar
                          name="Frequency"
                          dataKey="frequency_pct"
                          stroke="#1976d2"
                          fill="#1976d2"
                          fillOpacity={0.3}
                          strokeWidth={2}
                          dot={{ fill: '#1976d2', strokeWidth: 2, r: 3 }}
                        />
                        <RechartsTooltip content={<RadarTooltip />} />
                      </RadarChart>
                    </ResponsiveContainer>
                  </Box>

                  {/* Intentions Details */}
                  <Box sx={{ mt: 2, maxHeight: 200, overflowY: 'auto' }}>
                    <Typography variant="caption" color="text.secondary" gutterBottom>
                      Intention Details:
                    </Typography>
                    {playerIntentions.slice(0, 5).map((intention, index) => (
                      <Box 
                        key={intention.intention} 
                        sx={{ 
                          mb: 0.5, 
                          p: 0.5, 
                          cursor: 'pointer',
                          '&:hover': { backgroundColor: '#f5f5f5' },
                          borderRadius: 0.5
                        }}
                        onClick={() => handleIntentionClick(intention)}
                      >
                        <Typography variant="caption" display="block">
                          <strong>{intention.intention}:</strong> {intention.n_actions} actions ({intention.frequency_pct}%)
                        </Typography>
                      </Box>
                    ))}
                    {playerIntentions.length > 5 && (
                      <Typography variant="caption" color="text.secondary">
                        ...and {playerIntentions.length - 5} more intentions
                      </Typography>
                    )}
                  </Box>
                </Paper>
              ) : (
                filters.player && (
                  <Paper sx={{ p: 2 }}>
                    <Typography variant="h6" gutterBottom>
                      Player Intentions
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      No intention data available for this player.
                      {hasSearched && " Try analyzing with more actions or check data availability."}
                    </Typography>
                  </Paper>
                )
              )}
            </Grid>
          </Grid>
        </Box>
      )}

      {!loading && hasSearched && data.length === 0 && (
        <Alert severity="info" sx={{ mt: 3 }}>
          No betting data found with the specified criteria. Try adjusting your filters.
        </Alert>
      )}

      {/* Hand History Viewer Dialog */}
      <Dialog 
        open={showHandViewer} 
        onClose={() => setShowHandViewer(false)}
        maxWidth="lg"
        fullWidth
      >
        <DialogTitle>
          Hand Details
        </DialogTitle>
        <DialogContent>
          {selectedHandId && (
            <HandHistoryViewer 
              handId={selectedHandId} 
              onClose={() => setShowHandViewer(false)}
            />
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowHandViewer(false)}>
            Close
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default BettingVsStrength 