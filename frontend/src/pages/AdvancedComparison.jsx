import React, { useState, useEffect, useMemo } from 'react';
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
  Card,
  CardContent,
  Stack,
  IconButton,
  Collapse,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Skeleton,
  alpha,
  useTheme,
} from '@mui/material';
import {
  Search as SearchIcon,
  FilterList as FilterIcon,
  TrendingUp as TrendingUpIcon,
  Groups as UsersIcon,
  GpsFixed as TargetIcon,
  BarChart as BarChartIcon,
  Info as InfoIcon,
  Shield as ShieldIcon,
  Warning as AlertTriangleIcon,
  Timeline as ActivityIcon,
  ExpandMore as ChevronDownIcon,
  ExpandLess as ChevronUpIcon,
  Clear as ClearIcon,
} from '@mui/icons-material';
import { motion, AnimatePresence } from 'framer-motion';
import CountUp from 'react-countup';

// Animation variants
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1
    }
  }
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { 
    opacity: 1, 
    y: 0,
    transition: {
      duration: 0.4
    }
  }
};

// Enhanced stat card matching Dashboard style
const StatCard = ({ title, value, icon, color, subtitle, delay = 0 }) => {
  const [isHovered, setIsHovered] = useState(false);
  
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
            {subtitle && (
              <Chip
                size="small"
                label={`${subtitle > 0 ? '+' : ''}${subtitle}%`}
                sx={{
                  backgroundColor: alpha(subtitle > 0 ? '#00ff88' : '#ff4757', 0.2),
                  color: subtitle > 0 ? '#00ff88' : '#ff4757',
                  fontWeight: 600,
                }}
              />
            )}
          </Box>
          <Typography variant="h5" sx={{ fontWeight: 700, mb: 0.5 }}>
            {typeof value === 'number' ? (
              <CountUp end={value} duration={2} separator="," />
            ) : (
              value
            )}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {title}
          </Typography>
        </CardContent>
      </Card>
    </motion.div>
  );
};

const AdvancedComparison = () => {
  const [availableFilters, setAvailableFilters] = useState({});
  const [selectedPlayer, setSelectedPlayer] = useState('');
  const [comparisonPlayer, setComparisonPlayer] = useState('');
  const [filters, setFilters] = useState({});
  const [segmentData, setSegmentData] = useState(null);
  const [segmentHands, setSegmentHands] = useState([]);
  const [distribution, setDistribution] = useState([]);
  const [loading, setLoading] = useState(false);
  const [players, setPlayers] = useState([]);
  const [expandedInfo, setExpandedInfo] = useState(false);
  const theme = useTheme();

  // Load available filters on mount
  useEffect(() => {
    fetchAvailableFilters();
    fetchPlayers();
  }, []);

  const fetchAvailableFilters = async () => {
    try {
      const response = await fetch('/api/advanced-comparison/filters');
      const data = await response.json();
      if (data.success) {
        setAvailableFilters(data.filters);
      }
    } catch (error) {
      console.error('Error fetching filters:', error);
    }
  };

  const fetchPlayers = async () => {
    try {
      const response = await fetch('/api/players?limit=200');
      const data = await response.json();
      setPlayers(data.players || []);
    } catch (error) {
      console.error('Error fetching players:', error);
    }
  };

  const fetchSegmentData = async () => {
    if (!selectedPlayer) return;

    setLoading(true);
    try {
      // Build query params
      const params = new URLSearchParams({ player_id: selectedPlayer });
      if (comparisonPlayer) params.append('comparison_player_id', comparisonPlayer);
      
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== '' && value !== null && value !== undefined) {
          params.append(key, value);
        }
      });

      // Fetch segment data
      const segmentResponse = await fetch(`/api/advanced-comparison/segment?${params}`);
      const segmentResult = await segmentResponse.json();
      if (segmentResult.success) {
        setSegmentData(segmentResult.data);
      }

      // Fetch hands matching segment
      const handsResponse = await fetch(`/api/advanced-comparison/hands?${params}&limit=10`);
      const handsResult = await handsResponse.json();
      if (handsResult.success) {
        setSegmentHands(handsResult.hands);
      }

      // Fetch distribution
      const distParams = new URLSearchParams(params);
      distParams.delete('player_id');
      distParams.delete('comparison_player_id');
      distParams.append('group_by', 'player_id');
      
      const distResponse = await fetch(`/api/advanced-comparison/distribution?${distParams}`);
      const distResult = await distResponse.json();
      if (distResult.success) {
        setDistribution(distResult.distribution);
      }
    } catch (error) {
      console.error('Error fetching segment data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = (filterName, value) => {
    setFilters(prev => ({
      ...prev,
      [filterName]: value === '' ? undefined : value
    }));
  };

  const formatNumber = (num) => {
    if (num === null || num === undefined) return '-';
    return Number(num).toFixed(1);
  };

  const formatPercent = (num) => {
    if (num === null || num === undefined) return '-';
    return `${Number(num).toFixed(1)}%`;
  };

  const getActiveFiltersCount = () => {
    return Object.values(filters).filter(v => v !== '' && v !== null && v !== undefined).length;
  };

  const clearFilters = () => {
    setFilters({});
  };

  // Calculate risk score
  const getRiskScore = (stats) => {
    if (!stats || !stats.avg_j_score) return 'N/A';
    const score = stats.avg_j_score;
    if (score < 30) return 'HIGH';
    if (score < 50) return 'MEDIUM';
    return 'LOW';
  };

  return (
    <Box>
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <Typography 
          variant="h4" 
          gutterBottom
          sx={{
            fontWeight: 700,
            background: 'linear-gradient(135deg, #00d4ff 0%, #00ff88 100%)',
            backgroundClip: 'text',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
          }}
        >
          Player Segmentation Analysis
        </Typography>
        <Typography variant="subtitle1" sx={{ color: 'text.secondary', mb: 3 }}>
          Advanced fraud detection through behavioral segmentation and pattern analysis
        </Typography>
      </motion.div>

      {/* Player Selection */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.1 }}
      >
        <Paper 
          sx={{ 
            p: 3, 
            mb: 3,
            background: 'linear-gradient(135deg, rgba(17, 24, 39, 0.9) 0%, rgba(17, 24, 39, 0.7) 100%)',
            backdropFilter: 'blur(10px)',
            border: '1px solid rgba(255, 255, 255, 0.05)',
          }}
        >
          <Box display="flex" alignItems="center" gap={2} mb={3}>
            <ShieldIcon sx={{ color: '#00d4ff', fontSize: 28 }} />
            <Typography variant="h6" sx={{ fontWeight: 600, color: '#00d4ff' }}>
              Target Selection
            </Typography>
          </Box>
          
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <FormControl fullWidth>
                <InputLabel>Primary Target *</InputLabel>
                <Select
              value={selectedPlayer}
              onChange={(e) => setSelectedPlayer(e.target.value)}
                  label="Primary Target *"
                  sx={{
                    '& .MuiOutlinedInput-notchedOutline': {
                      borderColor: 'rgba(255, 255, 255, 0.2)',
                    },
                    '&:hover .MuiOutlinedInput-notchedOutline': {
                      borderColor: '#00d4ff',
                    },
                  }}
                >
                  <MenuItem value="">Select a player...</MenuItem>
              {players.map(player => (
                    <MenuItem key={player.player_id} value={player.player_id}>
                  {player.nickname || player.player_id} ({player.hands_played} hands)
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            
            <Grid item xs={12} md={6}>
              <FormControl fullWidth>
                <InputLabel>Compare With (Optional)</InputLabel>
                <Select
              value={comparisonPlayer}
              onChange={(e) => setComparisonPlayer(e.target.value)}
                  label="Compare With (Optional)"
                  sx={{
                    '& .MuiOutlinedInput-notchedOutline': {
                      borderColor: 'rgba(255, 255, 255, 0.2)',
                    },
                    '&:hover .MuiOutlinedInput-notchedOutline': {
                      borderColor: '#00d4ff',
                    },
                  }}
                >
                  <MenuItem value="">No comparison...</MenuItem>
              {players.filter(p => p.player_id !== selectedPlayer).map(player => (
                    <MenuItem key={player.player_id} value={player.player_id}>
                  {player.nickname || player.player_id} ({player.hands_played} hands)
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
          </Grid>
        </Paper>
      </motion.div>

      {/* Filters */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.2 }}
      >
        <Paper 
          sx={{ 
            p: 3, 
            mb: 3,
            background: 'linear-gradient(135deg, rgba(17, 24, 39, 0.9) 0%, rgba(17, 24, 39, 0.7) 100%)',
            backdropFilter: 'blur(10px)',
            border: '1px solid rgba(255, 255, 255, 0.05)',
          }}
        >
          <Box display="flex" alignItems="center" justifyContent="space-between" mb={3}>
            <Box display="flex" alignItems="center" gap={2}>
              <FilterIcon sx={{ color: '#00d4ff', fontSize: 28 }} />
              <Typography variant="h6" sx={{ fontWeight: 600, color: '#00d4ff' }}>
            Segment Filters
              </Typography>
              {getActiveFiltersCount() > 0 && (
                <Chip
                  label={`${getActiveFiltersCount()} active`}
                  size="small"
                  sx={{
                    backgroundColor: alpha('#00d4ff', 0.2),
                    color: '#00d4ff',
                    fontWeight: 600,
                  }}
                />
              )}
            </Box>
            {getActiveFiltersCount() > 0 && (
              <Button
                size="small"
                startIcon={<ClearIcon />}
              onClick={clearFilters}
                sx={{ color: '#ff4757' }}
            >
              Clear all filters
              </Button>
          )}
          </Box>

          <Grid container spacing={2}>
          {/* Street Filter */}
            <Grid item xs={12} sm={6} md={4}>
              <FormControl fullWidth size="small">
                <InputLabel>Street</InputLabel>
                <Select
              value={filters.street || ''}
              onChange={(e) => handleFilterChange('street', e.target.value)}
                  label="Street"
            >
                  <MenuItem value="">All streets</MenuItem>
              {availableFilters.streets?.map(street => (
                    <MenuItem key={street} value={street}>{street}</MenuItem>
              ))}
                </Select>
              </FormControl>
            </Grid>

          {/* Position Filter */}
            <Grid item xs={12} sm={6} md={4}>
              <FormControl fullWidth size="small">
                <InputLabel>Position</InputLabel>
                <Select
              value={filters.position || ''}
              onChange={(e) => handleFilterChange('position', e.target.value)}
                  label="Position"
            >
                  <MenuItem value="">All positions</MenuItem>
              {availableFilters.positions?.map(pos => (
                    <MenuItem key={pos} value={pos}>{pos}</MenuItem>
              ))}
                </Select>
              </FormControl>
            </Grid>

          {/* Action Label Filter */}
            <Grid item xs={12} sm={6} md={4}>
              <FormControl fullWidth size="small">
                <InputLabel>Action</InputLabel>
                <Select
              value={filters.action_label || ''}
              onChange={(e) => handleFilterChange('action_label', e.target.value)}
                  label="Action"
            >
                  <MenuItem value="">All actions</MenuItem>
              {availableFilters.action_labels?.map(action => (
                    <MenuItem key={action} value={action}>{action}</MenuItem>
              ))}
                </Select>
              </FormControl>
            </Grid>

          {/* J-Score Range */}
            <Grid item xs={12} md={8}>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                J-Score Range
              </Typography>
              <Box display="flex" gap={2} alignItems="center">
                <TextField
                type="number"
                placeholder="Min"
                value={filters.min_j_score || ''}
                onChange={(e) => handleFilterChange('min_j_score', e.target.value)}
                  size="small"
                  fullWidth
                  inputProps={{ min: 0, max: 100 }}
                />
                <Typography color="text.secondary">-</Typography>
                <TextField
                type="number"
                placeholder="Max"
                value={filters.max_j_score || ''}
                onChange={(e) => handleFilterChange('max_j_score', e.target.value)}
                  size="small"
                  fullWidth
                  inputProps={{ min: 0, max: 100 }}
                />
              </Box>
            </Grid>

          {/* Pot Type */}
            <Grid item xs={12} sm={6} md={4}>
              <FormControl fullWidth size="small">
                <InputLabel>Pot Type</InputLabel>
                <Select
              value={filters.pot_type || ''}
              onChange={(e) => handleFilterChange('pot_type', e.target.value)}
                  label="Pot Type"
            >
                  <MenuItem value="">All pot types</MenuItem>
              {availableFilters.pot_types?.map(type => (
                    <MenuItem key={type} value={type}>{type}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
          </Grid>

          <AnimatePresence>
          {expandedInfo && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.3 }}
              >
                <Grid container spacing={2} sx={{ mt: 2 }}>
                  {/* Additional filters */}
                  <Grid item xs={12} md={8}>
                    <Typography variant="body2" color="text.secondary" gutterBottom>
                      Preflop Score Range
                    </Typography>
                    <Box display="flex" gap={2} alignItems="center">
                      <TextField
                    type="number"
                    placeholder="Min"
                    value={filters.min_preflop_score || ''}
                    onChange={(e) => handleFilterChange('min_preflop_score', e.target.value)}
                        size="small"
                        fullWidth
                        inputProps={{ min: 0, max: 100 }}
                      />
                      <Typography color="text.secondary">-</Typography>
                      <TextField
                    type="number"
                    placeholder="Max"
                    value={filters.max_preflop_score || ''}
                    onChange={(e) => handleFilterChange('max_preflop_score', e.target.value)}
                        size="small"
                        fullWidth
                        inputProps={{ min: 0, max: 100 }}
                      />
                    </Box>
                  </Grid>

                  <Grid item xs={12} sm={6} md={4}>
                    <FormControl fullWidth size="small">
                      <InputLabel>Size Category</InputLabel>
                      <Select
                  value={filters.size_cat || ''}
                  onChange={(e) => handleFilterChange('size_cat', e.target.value)}
                        label="Size Category"
                >
                        <MenuItem value="">All sizes</MenuItem>
                  {availableFilters.size_categories?.map(size => (
                          <MenuItem key={size} value={size}>{size}</MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                  </Grid>
                </Grid>
              </motion.div>
            )}
          </AnimatePresence>

          <Box display="flex" alignItems="center" justifyContent="space-between" mt={3}>
            <Button
              size="small"
              startIcon={expandedInfo ? <ChevronUpIcon /> : <ChevronDownIcon />}
            onClick={() => setExpandedInfo(!expandedInfo)}
              sx={{ color: '#00d4ff' }}
          >
            {expandedInfo ? 'Show fewer filters' : 'Show more filters'}
            </Button>
          
            <Button
              variant="contained"
              startIcon={loading ? <CircularProgress size={16} /> : <SearchIcon />}
            onClick={fetchSegmentData}
            disabled={!selectedPlayer || loading}
              sx={{
                background: 'linear-gradient(135deg, #00d4ff 0%, #00a8cc 100%)',
                '&:hover': {
                  background: 'linear-gradient(135deg, #4de3ff 0%, #00d4ff 100%)',
                },
                '&:disabled': {
                  opacity: 0.5,
                },
              }}
            >
              {loading ? 'Analyzing...' : 'Analyze Segment'}
            </Button>
          </Box>
        </Paper>
      </motion.div>

      {/* Results */}
      <AnimatePresence>
      {segmentData && (
          <motion.div
            variants={containerVariants}
            initial="hidden"
            animate="visible"
          >
          {/* Comparison Stats */}
            <motion.div variants={itemVariants}>
              <Paper 
                sx={{ 
                  p: 3, 
                  mb: 3,
                  background: 'linear-gradient(135deg, rgba(17, 24, 39, 0.9) 0%, rgba(17, 24, 39, 0.7) 100%)',
                  backdropFilter: 'blur(10px)',
                  border: '1px solid rgba(255, 255, 255, 0.05)',
                }}
              >
                <Box display="flex" alignItems="center" gap={2} mb={3}>
                  <ActivityIcon sx={{ color: '#00d4ff', fontSize: 28 }} />
                  <Typography variant="h6" sx={{ fontWeight: 600, color: '#00d4ff' }}>
                    Segment Analysis Results
                  </Typography>
                </Box>

                <Grid container spacing={3}>
              {/* Player Stats */}
                  <Grid item xs={12} md={4}>
                    <motion.div whileHover={{ scale: 1.02 }}>
                      <Card
                        sx={{
                          background: 'linear-gradient(135deg, rgba(0, 212, 255, 0.1) 0%, rgba(0, 212, 255, 0.05) 100%)',
                          border: '1px solid rgba(0, 212, 255, 0.3)',
                          height: '100%',
                        }}
                      >
                        <CardContent>
                          <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
                            <Typography variant="h6" sx={{ color: '#00d4ff', fontWeight: 600 }}>
                              {selectedPlayer}
                            </Typography>
                            <Chip
                              label={`Risk: ${getRiskScore(segmentData.player_stats)}`}
                              size="small"
                              sx={{
                                backgroundColor: alpha(
                                  getRiskScore(segmentData.player_stats) === 'HIGH' ? '#ff4757' :
                                  getRiskScore(segmentData.player_stats) === 'MEDIUM' ? '#ffa502' : '#00ff88',
                                  0.2
                                ),
                                color: getRiskScore(segmentData.player_stats) === 'HIGH' ? '#ff4757' :
                                       getRiskScore(segmentData.player_stats) === 'MEDIUM' ? '#ffa502' : '#00ff88',
                                fontWeight: 600,
                              }}
                            />
                          </Box>
                {segmentData.player_stats.action_count > 0 ? (
                            <Stack spacing={2}>
                              {[
                                { label: 'Actions', value: segmentData.player_stats.action_count },
                                { label: 'Hands', value: segmentData.player_stats.hand_count },
                                { label: 'Avg J-Score', value: formatNumber(segmentData.player_stats.avg_j_score) },
                                { label: 'Win Rate', value: formatPercent(segmentData.player_stats.win_rate), color: segmentData.player_stats.win_rate >= 0 ? '#00ff88' : '#ff4757' },
                                { label: 'Avg Raise Size', value: formatNumber(segmentData.player_stats.avg_raise_size) },
                              ].map((stat, idx) => (
                                <Box key={idx} display="flex" justifyContent="space-between" alignItems="center">
                                  <Typography variant="body2" color="text.secondary">{stat.label}:</Typography>
                                  <Typography variant="body2" sx={{ fontWeight: 600, color: stat.color || 'text.primary' }}>
                                    {typeof stat.value === 'number' && !stat.label.includes('J-Score') && !stat.label.includes('Size') ? 
                                      <CountUp end={stat.value} duration={1} /> : stat.value}
                                  </Typography>
                                </Box>
                              ))}
                            </Stack>
                          ) : (
                            <Typography variant="body2" color="text.secondary">No data for this segment</Typography>
                          )}
                        </CardContent>
                      </Card>
                    </motion.div>
                  </Grid>

              {/* Population Average */}
                  <Grid item xs={12} md={4}>
                    <motion.div whileHover={{ scale: 1.02 }}>
                      <Card
                        sx={{
                          background: 'linear-gradient(135deg, rgba(0, 255, 136, 0.1) 0%, rgba(0, 255, 136, 0.05) 100%)',
                          border: '1px solid rgba(0, 255, 136, 0.3)',
                          height: '100%',
                        }}
                      >
                        <CardContent>
                          <Typography variant="h6" sx={{ color: '#00ff88', fontWeight: 600, mb: 2 }}>
                  Population Average
                          </Typography>
                {segmentData.population_stats.total_actions > 0 ? (
                            <Stack spacing={2}>
                              {[
                                { label: 'Total Actions', value: segmentData.population_stats.total_actions },
                                { label: 'Unique Players', value: segmentData.population_stats.unique_players },
                                { label: 'Avg J-Score', value: formatNumber(segmentData.population_stats.avg_j_score) },
                                { label: 'Avg Win Rate', value: formatPercent(segmentData.population_stats.avg_win_rate), color: segmentData.population_stats.avg_win_rate >= 0 ? '#00ff88' : '#ff4757' },
                                { label: 'Avg Raise Size', value: formatNumber(segmentData.population_stats.avg_raise_size) },
                              ].map((stat, idx) => (
                                <Box key={idx} display="flex" justifyContent="space-between" alignItems="center">
                                  <Typography variant="body2" color="text.secondary">{stat.label}:</Typography>
                                  <Typography variant="body2" sx={{ fontWeight: 600, color: stat.color || 'text.primary' }}>
                                    {typeof stat.value === 'number' && !stat.label.includes('J-Score') && !stat.label.includes('Size') ? 
                                      <CountUp end={stat.value} duration={1} /> : stat.value}
                                  </Typography>
                                </Box>
                              ))}
                            </Stack>
                          ) : (
                            <Typography variant="body2" color="text.secondary">No population data for this segment</Typography>
                          )}
                        </CardContent>
                      </Card>
                    </motion.div>
                  </Grid>

              {/* Comparison Player */}
              {comparisonPlayer && (
                    <Grid item xs={12} md={4}>
                      <motion.div whileHover={{ scale: 1.02 }}>
                        <Card
                          sx={{
                            background: 'linear-gradient(135deg, rgba(147, 51, 234, 0.1) 0%, rgba(147, 51, 234, 0.05) 100%)',
                            border: '1px solid rgba(147, 51, 234, 0.3)',
                            height: '100%',
                          }}
                        >
                          <CardContent>
                            <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
                              <Typography variant="h6" sx={{ color: '#9333ea', fontWeight: 600 }}>
                                {comparisonPlayer}
                              </Typography>
                              <Chip
                                label={`Risk: ${getRiskScore(segmentData.comparison_stats)}`}
                                size="small"
                                sx={{
                                  backgroundColor: alpha(
                                    getRiskScore(segmentData.comparison_stats) === 'HIGH' ? '#ff4757' :
                                    getRiskScore(segmentData.comparison_stats) === 'MEDIUM' ? '#ffa502' : '#00ff88',
                                    0.2
                                  ),
                                  color: getRiskScore(segmentData.comparison_stats) === 'HIGH' ? '#ff4757' :
                                         getRiskScore(segmentData.comparison_stats) === 'MEDIUM' ? '#ffa502' : '#00ff88',
                                  fontWeight: 600,
                                }}
                              />
                            </Box>
                  {segmentData.comparison_stats?.action_count > 0 ? (
                              <Stack spacing={2}>
                                {[
                                  { label: 'Actions', value: segmentData.comparison_stats.action_count },
                                  { label: 'Hands', value: segmentData.comparison_stats.hand_count },
                                  { label: 'Avg J-Score', value: formatNumber(segmentData.comparison_stats.avg_j_score) },
                                  { label: 'Win Rate', value: formatPercent(segmentData.comparison_stats.win_rate), color: segmentData.comparison_stats.win_rate >= 0 ? '#00ff88' : '#ff4757' },
                                  { label: 'Avg Raise Size', value: formatNumber(segmentData.comparison_stats.avg_raise_size) },
                                ].map((stat, idx) => (
                                  <Box key={idx} display="flex" justifyContent="space-between" alignItems="center">
                                    <Typography variant="body2" color="text.secondary">{stat.label}:</Typography>
                                    <Typography variant="body2" sx={{ fontWeight: 600, color: stat.color || 'text.primary' }}>
                                      {typeof stat.value === 'number' && !stat.label.includes('J-Score') && !stat.label.includes('Size') ? 
                                        <CountUp end={stat.value} duration={1} /> : stat.value}
                                    </Typography>
                                  </Box>
                                ))}
                              </Stack>
                            ) : (
                              <Typography variant="body2" color="text.secondary">No data for this segment</Typography>
                            )}
                          </CardContent>
                        </Card>
                      </motion.div>
                    </Grid>
                  )}
                </Grid>

            {/* Performance vs Average */}
            {segmentData.player_stats.action_count > 0 && segmentData.population_stats.avg_j_score > 0 && (
                  <motion.div variants={itemVariants}>
                    <Box 
                      sx={{ 
                        mt: 3, 
                        p: 3, 
                        background: 'rgba(17, 24, 39, 0.5)',
                        borderRadius: 2,
                        border: '1px solid rgba(255, 255, 255, 0.05)',
                      }}
                    >
                      <Box display="flex" alignItems="center" gap={1} mb={2}>
                        <TrendingUpIcon sx={{ color: '#00d4ff', fontSize: 20 }} />
                        <Typography variant="h6" sx={{ fontWeight: 600, color: '#00d4ff' }}>
                          Performance Analysis
                        </Typography>
                      </Box>
                      <Grid container spacing={2}>
                        <Grid item xs={12} md={6}>
                          <Box 
                            sx={{ 
                              p: 2, 
                              background: 'rgba(17, 24, 39, 0.5)',
                              borderRadius: 1,
                              display: 'flex',
                              justifyContent: 'space-between',
                              alignItems: 'center',
                            }}
                          >
                            <Typography variant="body2" color="text.secondary">J-Score vs Population:</Typography>
                            <Box display="flex" alignItems="center" gap={1}>
                              {segmentData.player_stats.avg_j_score > segmentData.population_stats.avg_j_score ? '↑' : '↓'}
                              <Typography 
                                variant="body2" 
                                sx={{ 
                                  fontWeight: 600,
                                  color: segmentData.player_stats.avg_j_score > segmentData.population_stats.avg_j_score ? '#00ff88' : '#ff4757'
                                }}
                              >
                                {Math.abs(segmentData.player_stats.avg_j_score - segmentData.population_stats.avg_j_score).toFixed(1)}
                              </Typography>
                            </Box>
                          </Box>
                        </Grid>
                        <Grid item xs={12} md={6}>
                          <Box 
                            sx={{ 
                              p: 2, 
                              background: 'rgba(17, 24, 39, 0.5)',
                              borderRadius: 1,
                              display: 'flex',
                              justifyContent: 'space-between',
                              alignItems: 'center',
                            }}
                          >
                            <Typography variant="body2" color="text.secondary">Win Rate vs Population:</Typography>
                            <Box display="flex" alignItems="center" gap={1}>
                              {segmentData.player_stats.win_rate > segmentData.population_stats.avg_win_rate ? '↑' : '↓'}
                              <Typography 
                                variant="body2" 
                                sx={{ 
                                  fontWeight: 600,
                                  color: segmentData.player_stats.win_rate > segmentData.population_stats.avg_win_rate ? '#00ff88' : '#ff4757'
                                }}
                              >
                                {Math.abs(segmentData.player_stats.win_rate - segmentData.population_stats.avg_win_rate).toFixed(1)}%
                              </Typography>
                            </Box>
                          </Box>
                        </Grid>
                      </Grid>
                    </Box>
                  </motion.div>
                )}
              </Paper>
            </motion.div>

          {/* Top Players in Segment */}
          {distribution.length > 0 && (
              <motion.div variants={itemVariants}>
                <Paper 
                  sx={{ 
                    p: 3, 
                    mb: 3,
                    background: 'linear-gradient(135deg, rgba(17, 24, 39, 0.9) 0%, rgba(17, 24, 39, 0.7) 100%)',
                    backdropFilter: 'blur(10px)',
                    border: '1px solid rgba(255, 255, 255, 0.05)',
                  }}
                >
                  <Box display="flex" alignItems="center" gap={2} mb={3}>
                    <UsersIcon sx={{ color: '#00d4ff', fontSize: 28 }} />
                    <Typography variant="h6" sx={{ fontWeight: 600, color: '#00d4ff' }}>
                      Top Players in This Segment
                    </Typography>
                  </Box>
                  
                  <TableContainer>
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell sx={{ color: '#00d4ff', fontWeight: 600 }}>Player</TableCell>
                          <TableCell align="right" sx={{ color: '#00d4ff', fontWeight: 600 }}>Actions</TableCell>
                          <TableCell align="right" sx={{ color: '#00d4ff', fontWeight: 600 }}>Hands</TableCell>
                          <TableCell align="right" sx={{ color: '#00d4ff', fontWeight: 600 }}>Avg J-Score</TableCell>
                          <TableCell align="right" sx={{ color: '#00d4ff', fontWeight: 600 }}>Win Rate</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                    {distribution.slice(0, 10).map((item, idx) => (
                          <TableRow
                            key={idx}
                            component={motion.tr}
                            initial={{ opacity: 0, x: -20 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ duration: 0.3, delay: idx * 0.05 }}
                            sx={{
                              '&:hover': {
                                backgroundColor: 'rgba(0, 212, 255, 0.05)',
                              },
                            }}
                          >
                            <TableCell>{item.nickname || item.player_id}</TableCell>
                            <TableCell align="right">{item.action_count}</TableCell>
                            <TableCell align="right">{item.hand_count}</TableCell>
                            <TableCell align="right">{formatNumber(item.avg_j_score)}</TableCell>
                            <TableCell align="right">
                              <Chip
                                label={formatPercent(item.win_rate)}
                                size="small"
                                sx={{
                                  backgroundColor: alpha(item.win_rate >= 0 ? '#00ff88' : '#ff4757', 0.2),
                                  color: item.win_rate >= 0 ? '#00ff88' : '#ff4757',
                                  fontWeight: 600,
                                }}
                              />
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </Paper>
              </motion.div>
          )}

          {/* Sample Hands */}
          {segmentHands.length > 0 && (
              <motion.div variants={itemVariants}>
                <Paper 
                  sx={{ 
                    p: 3,
                    background: 'linear-gradient(135deg, rgba(17, 24, 39, 0.9) 0%, rgba(17, 24, 39, 0.7) 100%)',
                    backdropFilter: 'blur(10px)',
                    border: '1px solid rgba(255, 255, 255, 0.05)',
                  }}
                >
                  <Box display="flex" alignItems="center" gap={2} mb={3}>
                    <TargetIcon sx={{ color: '#00d4ff', fontSize: 28 }} />
                    <Typography variant="h6" sx={{ fontWeight: 600, color: '#00d4ff' }}>
                      Sample Hands from Segment
                    </Typography>
                  </Box>
                  
                  <Stack spacing={2}>
                {segmentHands.map((hand, idx) => (
                      <motion.div
                        key={idx}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.3, delay: idx * 0.05 }}
                        whileHover={{ scale: 1.01 }}
                      >
                        <Card
                          sx={{
                            p: 2,
                            background: 'rgba(17, 24, 39, 0.5)',
                            border: '1px solid rgba(255, 255, 255, 0.05)',
                            '&:hover': {
                              borderColor: 'rgba(0, 212, 255, 0.3)',
                              background: 'rgba(17, 24, 39, 0.7)',
                            },
                            transition: 'all 0.3s ease',
                          }}
                        >
                          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                            <Box>
                              <Typography variant="body2" sx={{ fontWeight: 600 }}>
                                {hand.hand_id}
                              </Typography>
                              <Typography variant="caption" color="text.secondary">
                                {hand.hand_date}
                              </Typography>
                            </Box>
                            <Box display="flex" gap={1}>
                              <Chip label={hand.position} size="small" sx={{ backgroundColor: alpha('#00d4ff', 0.2), color: '#00d4ff' }} />
                              <Chip label={hand.street} size="small" sx={{ backgroundColor: alpha('#00ff88', 0.2), color: '#00ff88' }} />
                            </Box>
                          </Box>
                          
                          <Grid container spacing={2}>
                            <Grid item xs={6} sm={3}>
                              <Typography variant="caption" color="text.secondary">Action:</Typography>
                              <Typography variant="body2" sx={{ fontWeight: 600 }}>{hand.action_label}</Typography>
                            </Grid>
                            <Grid item xs={6} sm={3}>
                              <Typography variant="caption" color="text.secondary">J-Score:</Typography>
                              <Typography variant="body2" sx={{ fontWeight: 600 }}>{formatNumber(hand.j_score)}</Typography>
                            </Grid>
                            <Grid item xs={6} sm={3}>
                              <Typography variant="caption" color="text.secondary">Size:</Typography>
                              <Typography variant="body2" sx={{ fontWeight: 600 }}>{formatNumber(hand.size_frac)}</Typography>
                            </Grid>
                            <Grid item xs={6} sm={3}>
                              <Typography variant="caption" color="text.secondary">Won:</Typography>
                              <Typography variant="body2" sx={{ fontWeight: 600, color: hand.money_won > 0 ? '#00ff88' : '#ff4757' }}>
                          {hand.money_won > 0 ? '+' : ''}{formatNumber(hand.money_won)}
                              </Typography>
                            </Grid>
                          </Grid>
                          
                    {hand.holecards && (
                            <Box mt={2}>
                              <Typography variant="caption" color="text.secondary">Cards:</Typography>
                              <Typography variant="body2" sx={{ fontFamily: 'monospace', ml: 1 }}>
                                {hand.holecards}
                        {hand.board_cards && (
                          <>
                                    <span style={{ color: 'text.secondary', margin: '0 8px' }}>|</span>
                                    {hand.board_cards}
                          </>
                        )}
                              </Typography>
                            </Box>
                    )}
                        </Card>
                      </motion.div>
                ))}
                  </Stack>
                </Paper>
              </motion.div>
          )}
          </motion.div>
      )}
      </AnimatePresence>
    </Box>
  );
};

export default AdvancedComparison; 