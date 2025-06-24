import React, { useState, useEffect } from 'react'
import {
  Box,
  Paper,
  Typography,
  Grid,
  Button,
  TextField,
  MenuItem,
  Chip,
  Card,
  CardContent,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  CircularProgress,
  Avatar,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Divider,
  Alert,
  useTheme,
  alpha,
  IconButton,
  Tooltip,
} from '@mui/material'
import {
  ExpandMore as ExpandMoreIcon,
  TrendingUp as TrendingUpIcon,
  People as PeopleIcon,
  FilterList as FilterIcon,
  Psychology as BrainIcon,
  Casino as CasinoIcon,
  Insights as InsightsIcon,
  Clear as ClearIcon,
  Speed as SpeedIcon,
  Timeline as TimelineIcon,
  Analytics as AnalyticsIcon,
  MyLocation as CrosshairsIcon,
  Assignment as AssignmentIcon,
} from '@mui/icons-material'
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip as ChartTooltip, 
  Legend, 
  ResponsiveContainer, 
  RadarChart, 
  PolarGrid, 
  PolarAngleAxis, 
  PolarRadiusAxis, 
  Radar,
  LineChart,
  Line,
} from 'recharts'

function AdvancedComparison() {
  const theme = useTheme()
  const [availableFilters, setAvailableFilters] = useState({})
  const [selectedPlayer, setSelectedPlayer] = useState('')
  const [comparisonPlayer, setComparisonPlayer] = useState('')
  const [filters, setFilters] = useState({})
  const [segmentData, setSegmentData] = useState(null)
  const [segmentHands, setSegmentHands] = useState([])
  const [distribution, setDistribution] = useState([])
  const [loading, setLoading] = useState(false)
  const [players, setPlayers] = useState([])
  const [expandedFilters, setExpandedFilters] = useState(false)
  const [generalStats, setGeneralStats] = useState(null)

  useEffect(() => {
    fetchAvailableFilters()
    fetchPlayers()
  }, [])

  useEffect(() => {
    if (selectedPlayer) {
      fetchGeneralPlayerStats()
    }
  }, [selectedPlayer])

  const fetchAvailableFilters = async () => {
    try {
      const response = await fetch('/api/advanced-comparison/filters')
      const data = await response.json()
      if (data.success) {
        setAvailableFilters(data.filters)
      }
    } catch (error) {
      console.error('Error fetching filters:', error)
    }
  }

  const fetchPlayers = async () => {
    try {
      const response = await fetch('/api/players?limit=200')
      const data = await response.json()
      setPlayers(data.players || [])
    } catch (error) {
      console.error('Error fetching players:', error)
    }
  }

  const fetchGeneralPlayerStats = async () => {
    try {
      const response = await fetch(`/api/player/${selectedPlayer}/stats`)
      const data = await response.json()
      setGeneralStats(data)
    } catch (error) {
      console.error('Error fetching general stats:', error)
    }
  }

  const fetchSegmentData = async () => {
    if (!selectedPlayer) return

    setLoading(true)
    try {
      const params = new URLSearchParams({ player_id: selectedPlayer })
      if (comparisonPlayer) params.append('comparison_player_id', comparisonPlayer)
      
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== '' && value !== null && value !== undefined) {
          params.append(key, value)
        }
      })

      const [segmentResponse, handsResponse, distResponse] = await Promise.all([
        fetch(`/api/advanced-comparison/segment?${params}`),
        fetch(`/api/advanced-comparison/hands?${params}&limit=10`),
        fetch(`/api/advanced-comparison/distribution?${new URLSearchParams({...Object.fromEntries(params), group_by: 'player_id'})}`)
      ])

      const [segmentResult, handsResult, distResult] = await Promise.all([
        segmentResponse.json(),
        handsResponse.json(),
        distResponse.json()
      ])

      if (segmentResult.success) setSegmentData(segmentResult.data)
      if (handsResult.success) setSegmentHands(handsResult.hands)
      if (distResult.success) setDistribution(distResult.distribution)
    } catch (error) {
      console.error('Error fetching segment data:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleFilterChange = (filterName, value) => {
    setFilters(prev => ({
      ...prev,
      [filterName]: value === '' ? undefined : value
    }))
  }

  const clearFilters = () => {
    setFilters({})
  }

  const getActiveFiltersCount = () => {
    return Object.values(filters).filter(v => v !== '' && v !== null && v !== undefined).length
  }

  const formatNumber = (num) => {
    if (num === null || num === undefined) return '-'
    return Number(num).toFixed(1)
  }

  const formatPercent = (num) => {
    if (num === null || num === undefined) return '-'
    return `${Number(num).toFixed(1)}%`
  }

  const getComparisonChartData = () => {
    if (!segmentData?.player_stats || !segmentData?.population_stats) return []
    
    const stats = ['avg_j_score', 'win_rate', 'avg_raise_size']
    const labels = ['J-Score', 'Win Rate %', 'Avg Raise Size']
    
    return stats.map((stat, idx) => ({
      metric: labels[idx],
      [selectedPlayer]: segmentData.player_stats[stat] || 0,
      'Population Avg': segmentData.population_stats[stat === 'win_rate' ? 'avg_win_rate' : stat] || 0,
      ...(comparisonPlayer && segmentData.comparison_stats ? {
        [comparisonPlayer]: segmentData.comparison_stats[stat] || 0
      } : {})
    }))
  }

  const getActionDistributionData = () => {
    if (!segmentData?.player_stats) return []
    
    const total = (segmentData.player_stats.raise_count || 0) + 
                  (segmentData.player_stats.call_count || 0) + 
                  (segmentData.player_stats.fold_count || 0) +
                  (segmentData.player_stats.check_count || 0)
    
    if (total === 0) return []
    
    return [
      { action: 'Raise', value: ((segmentData.player_stats.raise_count || 0) / total * 100) },
      { action: 'Call', value: ((segmentData.player_stats.call_count || 0) / total * 100) },
      { action: 'Fold', value: ((segmentData.player_stats.fold_count || 0) / total * 100) },
      { action: 'Check', value: ((segmentData.player_stats.check_count || 0) / total * 100) }
    ]
  }

  const quickActionButtons = ['bet', 'checkraise', 'donk', 'cont', 'probe', 'lead', '2bet', '3bet']
    
    return (
    <Box sx={{ p: { xs: 2, md: 3 } }}>
      {/* Hero Header */}
      <Box mb={6} textAlign="center">
        <Typography 
          variant="h3" 
          gutterBottom 
          sx={{ 
            background: `linear-gradient(135deg, ${theme.palette.primary.main} 0%, ${theme.palette.secondary.main} 100%)`,
            backgroundClip: 'text',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            fontWeight: 700,
            mb: 2
          }}
        >
          Advanced Player Decision Analysis
        </Typography>
        <Typography variant="h6" color="text.secondary" sx={{ maxWidth: 800, mx: 'auto' }}>
          Deep dive into specific decision patterns with surgical precision. Segment player actions and compare against population benchmarks.
        </Typography>
      </Box>

      {/* Player Selection */}
      <Paper sx={{ 
        p: 4, 
        mb: 4, 
        background: `linear-gradient(145deg, ${alpha(theme.palette.background.paper, 0.9)} 0%, ${alpha(theme.palette.background.paper, 0.7)} 100%)`,
        backdropFilter: 'blur(20px)',
        border: `1px solid ${alpha(theme.palette.primary.main, 0.2)}`,
      }}>
        <Box display="flex" alignItems="center" gap={2} mb={3}>
          <Avatar sx={{ 
            background: `linear-gradient(135deg, ${theme.palette.primary.main} 0%, ${theme.palette.secondary.main} 100%)`,
            width: 48,
            height: 48
          }}>
            <PeopleIcon />
          </Avatar>
          <Typography variant="h5" sx={{ fontWeight: 600 }}>
          Player Selection
          </Typography>
        </Box>

        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Typography variant="subtitle2" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <CrosshairsIcon sx={{ fontSize: 16 }} />
              Primary Target Player *
            </Typography>
            <TextField
              select
              fullWidth
              id="selectedPlayer"
              name="selectedPlayer"
              value={selectedPlayer}
              onChange={(e) => setSelectedPlayer(e.target.value)}
              variant="outlined"
              sx={{
                '& .MuiOutlinedInput-root': {
                  borderRadius: 2,
                  '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
                    borderColor: theme.palette.primary.main,
                  },
                },
              }}
            >
              <MenuItem value="">Select a player to analyze...</MenuItem>
              {players.map(player => (
                <MenuItem key={player.player_id} value={player.player_id}>
                  {player.nickname || player.player_id} ({player.hands_played} hands)
                </MenuItem>
              ))}
            </TextField>
          </Grid>
          
          <Grid item xs={12} md={6}>
            <Typography variant="subtitle2" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <TimelineIcon sx={{ fontSize: 16 }} />
              Comparison Player (Optional)
            </Typography>
            <TextField
              select
              fullWidth
              id="comparisonPlayer"
              name="comparisonPlayer"
              value={comparisonPlayer}
              onChange={(e) => setComparisonPlayer(e.target.value)}
              variant="outlined"
              sx={{
                '& .MuiOutlinedInput-root': {
                  borderRadius: 2,
                  '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
                    borderColor: theme.palette.primary.main,
                  },
                },
              }}
            >
              <MenuItem value="">No comparison player...</MenuItem>
              {players.filter(p => p.player_id !== selectedPlayer).map(player => (
                <MenuItem key={player.player_id} value={player.player_id}>
                  {player.nickname || player.player_id} ({player.hands_played} hands)
                </MenuItem>
              ))}
            </TextField>
          </Grid>
        </Grid>

        {/* Player Profile Card */}
        {selectedPlayer && generalStats && (
          <Card sx={{ mt: 3, background: alpha(theme.palette.primary.main, 0.05), border: `1px solid ${alpha(theme.palette.primary.main, 0.2)}` }}>
            <CardContent>
              <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <BrainIcon sx={{ color: theme.palette.primary.main }} />
                Player Profile: {selectedPlayer}
              </Typography>
              <Grid container spacing={3}>
                {[
                  { label: 'Total Hands', value: generalStats.total_hands || 0, color: theme.palette.primary.main },
                  { label: 'Avg J-Score', value: formatNumber(generalStats.avg_j_score), color: theme.palette.secondary.main },
                  { label: 'VPIP', value: formatPercent(generalStats.vpip), color: theme.palette.info.main },
                  { label: 'PFR', value: formatPercent(generalStats.pfr), color: theme.palette.warning.main }
                ].map((stat, idx) => (
                  <Grid item xs={6} md={3} key={idx}>
                    <Box textAlign="center">
                      <Typography variant="h4" sx={{ color: stat.color, fontWeight: 700 }}>
                        {stat.value}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {stat.label}
                      </Typography>
                    </Box>
                  </Grid>
                ))}
              </Grid>
            </CardContent>
          </Card>
        )}
      </Paper>

      {/* Advanced Filters */}
      <Paper sx={{ 
        p: 4, 
        mb: 4,
        background: `linear-gradient(145deg, ${alpha(theme.palette.background.paper, 0.9)} 0%, ${alpha(theme.palette.background.paper, 0.7)} 100%)`,
        backdropFilter: 'blur(20px)',
        border: `1px solid ${alpha(theme.palette.secondary.main, 0.2)}`,
      }}>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
          <Box display="flex" alignItems="center" gap={2}>
            <Avatar sx={{ 
              background: `linear-gradient(135deg, ${theme.palette.secondary.main} 0%, ${theme.palette.primary.main} 100%)`,
              width: 48,
              height: 48
            }}>
              <FilterIcon />
            </Avatar>
            <Typography variant="h5" sx={{ fontWeight: 600 }}>
              Decision Filters
            </Typography>
            {getActiveFiltersCount() > 0 && (
              <Chip 
                label={`${getActiveFiltersCount()} active`} 
                size="small" 
                color="primary" 
                variant="outlined" 
              />
            )}
          </Box>
          {getActiveFiltersCount() > 0 && (
            <Button
              onClick={clearFilters}
              color="error"
              startIcon={<ClearIcon />}
              size="small"
            >
              Clear all
            </Button>
          )}
        </Box>

        {/* Quick Action Buttons */}
        <Box mb={3}>
          <Typography variant="subtitle2" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <SpeedIcon sx={{ fontSize: 16 }} />
            Quick Action Filter
          </Typography>
          <Box display="flex" flexWrap="wrap" gap={1}>
            {quickActionButtons.map(action => (
              <Chip
                key={action}
                label={action}
                onClick={() => handleFilterChange('action_label', action)}
                color={filters.action_label === action ? 'primary' : 'default'}
                variant={filters.action_label === action ? 'filled' : 'outlined'}
                sx={{
                  transition: 'all 0.2s ease',
                  '&:hover': {
                    transform: 'translateY(-1px)',
                    boxShadow: theme.shadows[4],
                  },
                }}
              />
            ))}
          </Box>
        </Box>

        {/* Basic Filters */}
        <Grid container spacing={3} mb={3}>
          <Grid item xs={12} sm={6} md={4}>
            <TextField
              select
              fullWidth
              id="street"
              name="street"
              label="Street"
              value={filters.street || ''}
              onChange={(e) => handleFilterChange('street', e.target.value)}
              size="small"
            >
              <MenuItem value="">All streets</MenuItem>
              {availableFilters.streets?.map(street => (
                <MenuItem key={street} value={street}>{street}</MenuItem>
              ))}
            </TextField>
          </Grid>
          
          <Grid item xs={12} sm={6} md={4}>
            <TextField
              select
              fullWidth
              id="position"
              name="position"
              label="Position"
              value={filters.position || ''}
              onChange={(e) => handleFilterChange('position', e.target.value)}
              size="small"
            >
              <MenuItem value="">All positions</MenuItem>
              {availableFilters.positions?.map(pos => (
                <MenuItem key={pos} value={pos}>{pos}</MenuItem>
              ))}
            </TextField>
          </Grid>

          <Grid item xs={12} sm={6} md={4}>
            <TextField
              select
              fullWidth
              id="actionType"
              name="actionType"
              label="Action Type"
              value={filters.action_label || ''}
              onChange={(e) => handleFilterChange('action_label', e.target.value)}
              size="small"
            >
              <MenuItem value="">All actions</MenuItem>
              {availableFilters.action_labels?.map(action => (
                <MenuItem key={action} value={action}>{action}</MenuItem>
              ))}
            </TextField>
          </Grid>

          <Grid item xs={12} sm={6} md={4}>
            <TextField
                type="number"
              fullWidth
              id="minJScore"
              name="minJScore"
              label="Min J-Score"
                value={filters.min_j_score || ''}
                onChange={(e) => handleFilterChange('min_j_score', e.target.value)}
              size="small"
              inputProps={{ min: 0, max: 100 }}
            />
          </Grid>

          <Grid item xs={12} sm={6} md={4}>
            <TextField
                type="number"
              fullWidth
              id="maxJScore"
              name="maxJScore"
              label="Max J-Score"
                value={filters.max_j_score || ''}
                onChange={(e) => handleFilterChange('max_j_score', e.target.value)}
              size="small"
              inputProps={{ min: 0, max: 100 }}
            />
          </Grid>

          <Grid item xs={12} sm={6} md={4}>
            <TextField
              select
              fullWidth
              id="potType"
              name="potType"
              label="Pot Type"
              value={filters.pot_type || ''}
              onChange={(e) => handleFilterChange('pot_type', e.target.value)}
              size="small"
            >
              <MenuItem value="">All pot types</MenuItem>
              {availableFilters.pot_types?.map(type => (
                <MenuItem key={type} value={type}>{type}</MenuItem>
              ))}
            </TextField>
          </Grid>
        </Grid>

        {/* Advanced Filters Accordion */}
        <Accordion expanded={expandedFilters} onChange={() => setExpandedFilters(!expandedFilters)}>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
              Advanced Filters
            </Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Grid container spacing={3}>
              <Grid item xs={12} sm={6} md={4}>
                <TextField
                  select
                  fullWidth
                  id="sizeCategory"
                  name="sizeCategory"
                  label="Size Category"
                  value={filters.size_cat || ''}
                  onChange={(e) => handleFilterChange('size_cat', e.target.value)}
                  size="small"
                >
                  <MenuItem value="">All sizes</MenuItem>
                  {availableFilters.size_categories?.map(size => (
                    <MenuItem key={size} value={size}>{size}</MenuItem>
                  ))}
                </TextField>
              </Grid>

              <Grid item xs={12} sm={6} md={4}>
                <TextField
                  select
                  fullWidth
                  id="ipStatus"
                  name="ipStatus"
                  label="IP Status"
                  value={filters.ip_status || ''}
                  onChange={(e) => handleFilterChange('ip_status', e.target.value)}
                  size="small"
                >
                  <MenuItem value="">All</MenuItem>
                  {availableFilters.ip_status?.map(status => (
                    <MenuItem key={status} value={status}>{status}</MenuItem>
                  ))}
                </TextField>
              </Grid>

              <Grid item xs={12} sm={6} md={4}>
                <TextField
                  select
                  fullWidth
                  id="intention"
                  name="intention"
                  label="Intention"
                  value={filters.intention || ''}
                  onChange={(e) => handleFilterChange('intention', e.target.value)}
                  size="small"
                >
                  <MenuItem value="">All intentions</MenuItem>
                  {availableFilters.intentions?.map(intention => (
                    <MenuItem key={intention} value={intention}>{intention}</MenuItem>
                  ))}
                </TextField>
              </Grid>
            </Grid>
          </AccordionDetails>
        </Accordion>

        {/* Analyze Button */}
        <Box display="flex" justifyContent="center" mt={4}>
          <Button
            onClick={fetchSegmentData}
            disabled={!selectedPlayer || loading}
            variant="contained"
            size="large"
            startIcon={loading ? <CircularProgress size={20} color="inherit" /> : <AnalyticsIcon />}
            sx={{
              px: 6,
              py: 2,
              fontSize: '1.1rem',
              fontWeight: 600,
              borderRadius: 3,
              background: `linear-gradient(135deg, ${theme.palette.primary.main} 0%, ${theme.palette.secondary.main} 100%)`,
              '&:hover': {
                background: `linear-gradient(135deg, ${theme.palette.primary.dark} 0%, ${theme.palette.secondary.dark} 100%)`,
                transform: 'translateY(-2px)',
                boxShadow: theme.shadows[8],
              },
              transition: 'all 0.3s ease',
            }}
          >
            {loading ? 'Analyzing...' : 'Analyze Decision Segment'}
          </Button>
        </Box>
      </Paper>

      {/* Results Section */}
      {segmentData && (
        <>
          {/* Performance Analysis Charts */}
          <Paper sx={{ p: 4, mb: 4 }}>
            <Typography variant="h5" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <TrendingUpIcon sx={{ color: theme.palette.primary.main }} />
              Performance Analysis
            </Typography>
            
            <Grid container spacing={4}>
              <Grid item xs={12} lg={8}>
                <Typography variant="h6" gutterBottom>Performance Metrics</Typography>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={getComparisonChartData()}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="metric" />
                    <YAxis />
                    <ChartTooltip 
                      contentStyle={{
                        backgroundColor: theme.palette.background.paper,
                        border: `1px solid ${theme.palette.divider}`,
                        borderRadius: theme.shape.borderRadius,
                      }}
                    />
                    <Legend />
                    <Bar dataKey={selectedPlayer} fill={theme.palette.primary.main} />
                    <Bar dataKey="Population Avg" fill={theme.palette.secondary.main} />
                    {comparisonPlayer && <Bar dataKey={comparisonPlayer} fill={theme.palette.info.main} />}
                  </BarChart>
                </ResponsiveContainer>
              </Grid>

              <Grid item xs={12} lg={4}>
                <Typography variant="h6" gutterBottom>Action Distribution</Typography>
                <ResponsiveContainer width="100%" height={300}>
                  <RadarChart data={getActionDistributionData()}>
                    <PolarGrid />
                    <PolarAngleAxis dataKey="action" />
                    <PolarRadiusAxis angle={90} domain={[0, 100]} />
                    <Radar 
                      name={selectedPlayer} 
                      dataKey="value" 
                      stroke={theme.palette.primary.main} 
                      fill={theme.palette.primary.main} 
                      fillOpacity={0.3} 
                    />
                  </RadarChart>
                </ResponsiveContainer>
              </Grid>
            </Grid>
          </Paper>

          {/* Segment Statistics */}
          <Paper sx={{ p: 4, mb: 4 }}>
            <Typography variant="h5" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <InsightsIcon sx={{ color: theme.palette.primary.main }} />
              Segment Analysis
            </Typography>

            <Grid container spacing={3}>
              {/* Player Stats */}
              <Grid item xs={12} md={4}>
                <Card sx={{ 
                  height: '100%', 
                  background: alpha(theme.palette.primary.main, 0.05),
                  border: `1px solid ${alpha(theme.palette.primary.main, 0.2)}`,
                }}>
                  <CardContent>
                    <Typography variant="h6" gutterBottom color="primary">
                      {selectedPlayer}
                    </Typography>
                {segmentData.player_stats.action_count > 0 ? (
                      <Box>
                        {[
                          ['Actions', segmentData.player_stats.action_count],
                          ['Hands', segmentData.player_stats.hand_count],
                          ['Avg J-Score', formatNumber(segmentData.player_stats.avg_j_score)],
                          ['Win Rate', formatPercent(segmentData.player_stats.win_rate)],
                        ].map(([label, value], idx) => (
                          <Box key={idx} display="flex" justifyContent="space-between" mb={1}>
                            <Typography variant="body2" color="text.secondary">{label}:</Typography>
                            <Typography variant="body2" fontWeight={600}>{value}</Typography>
                          </Box>
                        ))}
                        
                        <Divider sx={{ my: 2 }} />
                        <Typography variant="caption" color="text.secondary" gutterBottom display="block">
                          Action Breakdown:
                        </Typography>
                        <Grid container spacing={1}>
                          {[
                            ['Raises', segmentData.player_stats.raise_count || 0],
                            ['Calls', segmentData.player_stats.call_count || 0],
                            ['Folds', segmentData.player_stats.fold_count || 0],
                            ['Checks', segmentData.player_stats.check_count || 0],
                          ].map(([action, count], idx) => (
                            <Grid item xs={6} key={idx}>
                              <Box display="flex" justifyContent="space-between">
                                <Typography variant="caption">{action}:</Typography>
                                <Typography variant="caption" fontWeight={600}>{count}</Typography>
                              </Box>
                            </Grid>
                          ))}
                        </Grid>
                      </Box>
                    ) : (
                      <Alert severity="info">No data for this segment</Alert>
                    )}
                  </CardContent>
                </Card>
              </Grid>

              {/* Population Stats */}
              <Grid item xs={12} md={4}>
                <Card sx={{ 
                  height: '100%',
                  background: alpha(theme.palette.secondary.main, 0.05),
                  border: `1px solid ${alpha(theme.palette.secondary.main, 0.2)}`,
                }}>
                  <CardContent>
                    <Typography variant="h6" gutterBottom color="secondary">
                  Population Average
                    </Typography>
                {segmentData.population_stats.total_actions > 0 ? (
                      <Box>
                        {[
                          ['Total Actions', segmentData.population_stats.total_actions],
                          ['Unique Players', segmentData.population_stats.unique_players],
                          ['Avg J-Score', formatNumber(segmentData.population_stats.avg_j_score)],
                          ['Avg Win Rate', formatPercent(segmentData.population_stats.avg_win_rate)],
                        ].map(([label, value], idx) => (
                          <Box key={idx} display="flex" justifyContent="space-between" mb={1}>
                            <Typography variant="body2" color="text.secondary">{label}:</Typography>
                            <Typography variant="body2" fontWeight={600}>{value}</Typography>
                          </Box>
                        ))}
                      </Box>
                    ) : (
                      <Alert severity="info">No population data for this segment</Alert>
                    )}
                  </CardContent>
                </Card>
              </Grid>

              {/* Comparison Player */}
              {comparisonPlayer && segmentData.comparison_stats && (
                <Grid item xs={12} md={4}>
                  <Card sx={{ 
                    height: '100%',
                    background: alpha(theme.palette.info.main, 0.05),
                    border: `1px solid ${alpha(theme.palette.info.main, 0.2)}`,
                  }}>
                    <CardContent>
                      <Typography variant="h6" gutterBottom color="info.main">
                        {comparisonPlayer}
                      </Typography>
                      {segmentData.comparison_stats.action_count > 0 ? (
                        <Box>
                          {[
                            ['Actions', segmentData.comparison_stats.action_count],
                            ['Hands', segmentData.comparison_stats.hand_count],
                            ['Avg J-Score', formatNumber(segmentData.comparison_stats.avg_j_score)],
                          ].map(([label, value], idx) => (
                            <Box key={idx} display="flex" justifyContent="space-between" mb={1}>
                              <Typography variant="body2" color="text.secondary">{label}:</Typography>
                              <Typography variant="body2" fontWeight={600}>{value}</Typography>
                            </Box>
                          ))}
                        </Box>
                      ) : (
                        <Alert severity="info">No data for this segment</Alert>
                      )}
                    </CardContent>
                  </Card>
                </Grid>
              )}
            </Grid>

            {/* Performance vs Population */}
            {segmentData.player_stats.action_count > 0 && segmentData.population_stats.avg_j_score > 0 && (
              <Card sx={{ mt: 3, background: alpha(theme.palette.success.main, 0.05) }}>
                <CardContent>
                  <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <TrendingUpIcon />
                    Performance vs Population
                  </Typography>
                  <Grid container spacing={3}>
                    <Grid item xs={12} sm={6}>
                      <Box display="flex" justifyContent="space-between" alignItems="center">
                        <Typography>J-Score vs Population:</Typography>
                        <Typography 
                          variant="h6" 
                          sx={{ 
                            color: segmentData.player_stats.avg_j_score > segmentData.population_stats.avg_j_score 
                              ? theme.palette.success.main 
                              : theme.palette.error.main,
                            fontWeight: 700
                          }}
                        >
                      {segmentData.player_stats.avg_j_score > segmentData.population_stats.avg_j_score ? '+' : ''}
                      {formatNumber(segmentData.player_stats.avg_j_score - segmentData.population_stats.avg_j_score)}
                        </Typography>
                      </Box>
                    </Grid>
                    <Grid item xs={12} sm={6}>
                      <Box display="flex" justifyContent="space-between" alignItems="center">
                        <Typography>Win Rate vs Population:</Typography>
                        <Typography 
                          variant="h6" 
                          sx={{ 
                            color: segmentData.player_stats.win_rate > segmentData.population_stats.avg_win_rate 
                              ? theme.palette.success.main 
                              : theme.palette.error.main,
                            fontWeight: 700
                          }}
                        >
                      {segmentData.player_stats.win_rate > segmentData.population_stats.avg_win_rate ? '+' : ''}
                      {formatNumber(segmentData.player_stats.win_rate - segmentData.population_stats.avg_win_rate)}%
                        </Typography>
                      </Box>
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>
            )}
          </Paper>

          {/* Top Players in Segment */}
          {distribution.length > 0 && (
            <Paper sx={{ p: 4, mb: 4 }}>
              <Typography variant="h5" gutterBottom>
                Top Players in This Segment
              </Typography>
              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Player</TableCell>
                      <TableCell align="right">Actions</TableCell>
                      <TableCell align="right">Hands</TableCell>
                      <TableCell align="right">Avg J-Score</TableCell>
                      <TableCell align="right">Win Rate</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {distribution.slice(0, 10).map((item, idx) => (
                      <TableRow key={idx} hover>
                        <TableCell>
                          <Button
                            onClick={() => setSelectedPlayer(item.player_id)}
                            color="primary"
                            sx={{ textTransform: 'none' }}
                          >
                            {item.nickname || item.player_id}
                          </Button>
                        </TableCell>
                        <TableCell align="right">{item.action_count}</TableCell>
                        <TableCell align="right">{item.hand_count}</TableCell>
                        <TableCell align="right">{formatNumber(item.avg_j_score)}</TableCell>
                        <TableCell align="right">{formatPercent(item.win_rate)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </Paper>
          )}

          {/* Sample Hands */}
          {segmentHands.length > 0 && (
            <Paper sx={{ p: 4 }}>
              <Typography variant="h5" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <AssignmentIcon sx={{ color: theme.palette.primary.main }} />
                Sample Hands from Segment
              </Typography>
              <Grid container spacing={2}>
                {segmentHands.map((hand, idx) => (
                  <Grid item xs={12} key={idx}>
                    <Card variant="outlined" sx={{ '&:hover': { boxShadow: theme.shadows[4] } }}>
                      <CardContent>
                        <Box display="flex" justifyContent="space-between" alignItems="flex-start" mb={2}>
                          <Box>
                            <Typography variant="h6">{hand.hand_id}</Typography>
                            <Typography variant="caption" color="text.secondary">
                              {hand.hand_date}
                            </Typography>
                          </Box>
                          <Box display="flex" gap={1}>
                            <Chip label={hand.position} size="small" color="primary" />
                            <Chip label={hand.street} size="small" color="secondary" />
                          </Box>
                        </Box>
                        
                        <Grid container spacing={2}>
                          <Grid item xs={6} sm={3}>
                            <Typography variant="caption" color="text.secondary">Action:</Typography>
                            <Typography variant="body2" fontWeight={600}>{hand.action_label}</Typography>
                          </Grid>
                          <Grid item xs={6} sm={3}>
                            <Typography variant="caption" color="text.secondary">J-Score:</Typography>
                            <Typography variant="body2" fontWeight={600}>{formatNumber(hand.j_score)}</Typography>
                          </Grid>
                          <Grid item xs={6} sm={3}>
                            <Typography variant="caption" color="text.secondary">Size:</Typography>
                            <Typography variant="body2" fontWeight={600}>{formatNumber(hand.size_frac)}</Typography>
                          </Grid>
                          <Grid item xs={6} sm={3}>
                            <Typography variant="caption" color="text.secondary">Won:</Typography>
                            <Typography 
                              variant="body2" 
                              fontWeight={600}
                              color={hand.money_won > 0 ? 'success.main' : 'error.main'}
                            >
                          {hand.money_won > 0 ? '+' : ''}{formatNumber(hand.money_won)}
                            </Typography>
                          </Grid>
                        </Grid>
                        
                    {hand.holecards && (
                          <Box mt={2}>
                            <Typography variant="caption" color="text.secondary">Cards: </Typography>
                            <Typography variant="body2" component="span" sx={{ fontFamily: 'monospace' }}>
                              {hand.holecards}
                              {hand.board_cards && ` | ${hand.board_cards}`}
                            </Typography>
                          </Box>
                        )}
                      </CardContent>
                    </Card>
                  </Grid>
                ))}
              </Grid>
            </Paper>
          )}
        </>
      )}
    </Box>
  )
}

export default AdvancedComparison 