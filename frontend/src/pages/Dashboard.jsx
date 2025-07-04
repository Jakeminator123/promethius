import React, { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import Grid from '../mui-grid'
import {
  Paper,
  Typography,
  Box,
  Card,
  CardContent,
  LinearProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Checkbox,
  FormControlLabel,
  FormGroup,
  Skeleton,
  alpha,
  useTheme,
  TextField,
  Autocomplete,
  CircularProgress,
  ToggleButton,
  ToggleButtonGroup,
  Tooltip,
} from '@mui/material'
import {
  People as PeopleIcon,
  Casino as CasinoIcon,
  TrendingUp as TrendingUpIcon,
  EmojiEvents as TrophyIcon,
  Settings as SettingsIcon,
  Shield as ShieldIcon,
  Warning as WarningIcon,
  VerifiedUser as VerifiedIcon,
  Dangerous as DangerousIcon,
  CalendarToday as CalendarIcon,
  AttachMoney as CashIcon,
  WorkspacePremium as TournamentIcon,
  AutoAwesome as AIIcon,
  Psychology as AnalyzeIcon,
} from '@mui/icons-material'
import { motion, AnimatePresence } from 'framer-motion'
import CountUp from 'react-countup'
import { FixedSizeList as List } from 'react-window'
import axios from 'axios'

// Animation variants
const cardVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 },
  hover: { scale: 1.02, transition: { duration: 0.2 } }
}

const rowVariants = {
  hidden: { opacity: 0, x: -20 },
  visible: { opacity: 1, x: 0 },
  hover: { backgroundColor: 'rgba(0, 212, 255, 0.05)' }
}

// Enhanced stat card with animations
function StatCard({ title, value, icon, color, delay = 0, prefix = '', suffix = '', danger = false }) {
  const [isHovered, setIsHovered] = useState(false)
  const numericValue = typeof value === 'string' ? parseFloat(value.replace(/[^0-9.-]/g, '')) : value
  
  return (
    <motion.div
      initial="hidden"
      animate="visible"
      whileHover="hover"
      variants={cardVariants}
      transition={{ duration: 0.4, delay }}
      onHoverStart={() => setIsHovered(true)}
      onHoverEnd={() => setIsHovered(false)}
    >
      <Card
        sx={{
          background: danger 
            ? 'linear-gradient(135deg, rgba(255, 71, 87, 0.1) 0%, rgba(255, 71, 87, 0.05) 100%)'
            : 'linear-gradient(135deg, rgba(0, 212, 255, 0.05) 0%, rgba(0, 212, 255, 0.02) 100%)',
          backdropFilter: 'blur(10px)',
          border: danger
            ? '1px solid rgba(255, 71, 87, 0.3)'
            : '1px solid rgba(0, 212, 255, 0.2)',
          boxShadow: isHovered 
            ? danger
              ? '0 8px 32px rgba(255, 71, 87, 0.2)'
              : '0 8px 32px rgba(0, 212, 255, 0.2)'
            : '0 4px 24px rgba(0, 0, 0, 0.1)',
          transition: 'all 0.3s ease',
          minHeight: 120,
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <CardContent>
          <Box display="flex" alignItems="center" justifyContent="space-between">
            <Box>
              <Typography 
                variant="h6" 
                sx={{ 
                  color: 'text.secondary',
                  fontSize: '0.875rem',
                  fontWeight: 500,
                  mb: 1
                }}
              >
                {title}
              </Typography>
              <Typography variant="h3" sx={{ fontWeight: 700 }}>
                {!isNaN(numericValue) ? (
                  <>
                    {prefix}
                    <CountUp 
                      end={numericValue} 
                      duration={2.5} 
                      separator="," 
                      decimals={suffix === '%' || title.includes('Score') ? 1 : 0}
                    />
                    {suffix}
                  </>
                ) : (
                  value
                )}
              </Typography>
            </Box>
            <motion.div
              animate={{ 
                rotate: isHovered ? 360 : 0,
                scale: isHovered ? 1.2 : 1
              }}
              transition={{ duration: 0.5 }}
            >
              <Box 
                sx={{ 
                  color: color || 'primary.main',
                  opacity: 0.8,
                  filter: isHovered ? 'drop-shadow(0 0 8px currentColor)' : 'none',
                  transition: 'all 0.3s ease'
                }}
              >
                {icon}
              </Box>
            </motion.div>
          </Box>
        </CardContent>
      </Card>
    </motion.div>
  )
}

// Virtual table row component
const VirtualRow = ({ index, style, data }) => {
  const { players, handlePlayerClick, selectedColumns, analyzePlayer } = data
  const player = players[index]
  const navigate = useNavigate()
  
  // Risk assessment based on stats
  const getRiskLevel = (player) => {
    const avgJScore = player.avg_j_score || 0
    const winrate = player.winrate_bb100 || 0
    
    if (avgJScore < 30 || winrate < -20) return 'high'
    if (avgJScore < 50 || winrate < -5) return 'medium'
    return 'low'
  }
  
  const riskLevel = getRiskLevel(player)
  const riskColors = {
    high: '#ff4757',
    medium: '#ffa502',
    low: '#00ff88'
  }
  
  // Calculate Fraud Score
  const calculateFraudScore = () => {
    let score = 0
    
    // Base scores (always included)
    score += player.avg_preflop_score || 0
    score += player.avg_postflop_score || 0
    
    // Add optional column scores if selected
    if (selectedColumns.solver_precision_score && player.solver_precision_score != null) {
      score += player.solver_precision_score
    }
    if (selectedColumns.calldown_accuracy && player.calldown_accuracy != null) {
      score += player.calldown_accuracy
    }
    if (selectedColumns.bet_deviance && player.bet_deviance != null) {
      score += player.bet_deviance
    }
    if (selectedColumns.tilt_factor && player.tilt_factor != null) {
      score += player.tilt_factor
    }
    
    return score
  }
  
  const fraudScore = calculateFraudScore()
  
  // Get fraud score color based on value
  const getFraudScoreColor = (score) => {
    if (score > 250) return '#ff0040' // Extreme red
    if (score > 200) return '#ff4757' // High red
    if (score > 150) return '#ffa502' // Orange
    return '#00ff88' // Green (good)
  }
  
  const fraudScoreColor = getFraudScoreColor(fraudScore)
  
  return (
    <motion.div
      style={style}
      initial="hidden"
      animate="visible"
      whileHover="hover"
      variants={rowVariants}
      transition={{ duration: 0.2 }}
    >
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          px: 3,
          py: 2,
          borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
          cursor: 'pointer',
          '&:hover': {
            backgroundColor: alpha('#00d4ff', 0.05),
          }
        }}
        onClick={() => handlePlayerClick(player.player_id, player.nickname)}
      >
        <Box flex="0 0 40px" sx={{ mr: 2 }}>
          {index < 3 && (
            <motion.div
              animate={{ rotate: [0, 10, -10, 0] }}
              transition={{ duration: 2, repeat: Infinity, repeatDelay: 3 }}
            >
              <TrophyIcon 
                sx={{ 
                  fontSize: 20, 
                  color: index === 0 ? '#FFD700' : index === 1 ? '#C0C0C0' : '#CD7F32' 
                }} 
              />
            </motion.div>
          )}
        </Box>
        
        <Box flex="1 1 150px" sx={{ minWidth: 0 }}>
          <Typography 
            variant="body2" 
            sx={{ 
              fontWeight: 600,
              color: '#00d4ff',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap'
            }}
          >
            {player.nickname || player.player_id}
          </Typography>
        </Box>
        
        {/* AI Analyze button */}
        <Box flex="0 0 40px">
          <Tooltip title="AI Analysis" placement="top">
            <IconButton
              size="small"
              onClick={(e) => {
                e.stopPropagation()
                analyzePlayer(player)
              }}
              sx={{
                color: '#00ff88',
                '&:hover': {
                  backgroundColor: alpha('#00ff88', 0.1),
                },
              }}
            >
              <AIIcon sx={{ fontSize: 18 }} />
            </IconButton>
          </Tooltip>
        </Box>
        
        <Box flex="0 0 100px" sx={{ textAlign: 'right' }}>
          <Typography variant="body2" sx={{ fontWeight: 500 }}>
            {player.total_hands ? player.total_hands.toLocaleString() : '0'}
          </Typography>
        </Box>
        
        <Box flex="0 0 100px" sx={{ textAlign: 'right' }}>
          <Chip 
            label={`${(player.winrate_bb100 || 0).toFixed(2)} BB/100`}
            size="small"
            sx={{
              backgroundColor: alpha(player.winrate_bb100 > 0 ? '#00ff88' : '#ff4757', 0.2),
              color: player.winrate_bb100 > 0 ? '#00ff88' : '#ff4757',
              border: `1px solid ${player.winrate_bb100 > 0 ? '#00ff88' : '#ff4757'}`,
              fontWeight: 600
            }}
          />
        </Box>
        
        <Box flex="0 0 80px" sx={{ textAlign: 'right' }}>
          <Typography variant="body2">{(player.vpip || 0).toFixed(1)}%</Typography>
        </Box>
        
        <Box flex="0 0 80px" sx={{ textAlign: 'right' }}>
          <Typography variant="body2">{(player.pfr || 0).toFixed(1)}%</Typography>
        </Box>
        
        <Box flex="0 0 80px" sx={{ textAlign: 'right' }}>
          <Chip 
            label={player.avg_j_score?.toFixed(1) || '-'}
            size="small"
            sx={{
              backgroundColor: alpha('#00d4ff', 0.2),
              color: '#00d4ff',
              border: '1px solid #00d4ff',
              fontWeight: 600
            }}
          />
        </Box>
        
        <Box flex="0 0 80px" sx={{ textAlign: 'center' }}>
          <Chip 
            label={(player.avg_preflop_score || 0).toFixed(1)}
            size="small"
            sx={{
              backgroundColor: alpha('#a55eea', 0.2),
              color: '#a55eea',
              border: '1px solid #a55eea',
              fontWeight: 600
            }}
          />
        </Box>
        
        <Box flex="0 0 80px" sx={{ textAlign: 'center' }}>
          <Chip 
            label={(player.avg_postflop_score || 0).toFixed(1)}
            size="small"
            sx={{
              backgroundColor: alpha('#45aaf2', 0.2),
              color: '#45aaf2',
              border: '1px solid #45aaf2',
              fontWeight: 600
            }}
          />
        </Box>
        
        {!Object.values(selectedColumns).some(v => v) && (
          <Box flex="0 0 80px" sx={{ textAlign: 'right' }}>
            <Chip
              icon={
                riskLevel === 'high' ? <WarningIcon sx={{ fontSize: 16 }} /> :
                riskLevel === 'medium' ? <DangerousIcon sx={{ fontSize: 16 }} /> :
                <VerifiedIcon sx={{ fontSize: 16 }} />
              }
              label={riskLevel.toUpperCase()}
              size="small"
              sx={{
                backgroundColor: alpha(riskColors[riskLevel], 0.2),
                color: riskColors[riskLevel],
                border: `1px solid ${riskColors[riskLevel]}`,
                fontWeight: 600
              }}
            />
          </Box>
        )}
        
        {/* Extra columns */}
        {selectedColumns.solver_precision_score && (
          <Box flex="0 0 80px" sx={{ textAlign: 'center' }}>
            <Chip 
              label={player.solver_precision_score != null ? `${player.solver_precision_score}%` : '-'}
              size="small"
              sx={{
                backgroundColor: alpha('#00ff88', 0.2),
                color: '#00ff88',
                border: '1px solid #00ff88',
                fontWeight: 600
              }}
            />
          </Box>
        )}
        
        {selectedColumns.calldown_accuracy && (
          <Box flex="0 0 80px" sx={{ textAlign: 'center' }}>
            <Chip 
              label={player.calldown_accuracy != null ? `${player.calldown_accuracy}%` : '-'}
              size="small"
              sx={{
                backgroundColor: alpha('#ffa502', 0.2),
                color: '#ffa502',
                border: '1px solid #ffa502',
                fontWeight: 600
              }}
            />
          </Box>
        )}
        
        {selectedColumns.bet_deviance && (
          <Box flex="0 0 80px" sx={{ textAlign: 'center' }}>
            <Chip 
              label={player.bet_deviance != null ? `${player.bet_deviance}%` : '-'}
              size="small"
              sx={{
                backgroundColor: alpha('#ff6348', 0.2),
                color: '#ff6348',
                border: '1px solid #ff6348',
                fontWeight: 600
              }}
            />
          </Box>
        )}
        
        {selectedColumns.tilt_factor && (
          <Box flex="0 0 80px" sx={{ textAlign: 'center' }}>
            <Chip 
              label={player.tilt_factor != null ? `${player.tilt_factor}` : '-'}
              size="small"
              sx={{
                backgroundColor: alpha('#5f27cd', 0.2),
                color: '#5f27cd',
                border: '1px solid #5f27cd',
                fontWeight: 600
              }}
            />
          </Box>
        )}
        
        {/* Fraud Score - Always visible */}
        <Box flex="0 0 100px" sx={{ 
          textAlign: 'center',
          borderLeft: '2px solid rgba(255, 71, 87, 0.3)',
          pl: 1,
          background: `linear-gradient(90deg, 
            transparent 0%, 
            ${alpha('#ff4757', 0.05)} 50%, 
            transparent 100%)`,
        }}>
          <Tooltip 
            title={`Total: ${player.avg_preflop_score || 0} (pre) + ${player.avg_postflop_score || 0} (post) + ${
              selectedColumns.solver_precision_score && player.solver_precision_score != null ? player.solver_precision_score : 0
            } + ${
              selectedColumns.calldown_accuracy && player.calldown_accuracy != null ? player.calldown_accuracy : 0
            } + ${
              selectedColumns.bet_deviance && player.bet_deviance != null ? player.bet_deviance : 0
            } + ${
              selectedColumns.tilt_factor && player.tilt_factor != null ? player.tilt_factor : 0
            }`} 
            placement="left"
            arrow
          >
            <motion.div
              initial={{ scale: 0.8 }}
              animate={{ scale: 1 }}
              transition={{ duration: 0.3 }}
              style={{ display: 'inline-block' }}
            >
              <Chip 
                label={fraudScore.toFixed(1)}
                size="small"
                sx={{
                  backgroundColor: alpha(fraudScoreColor, 0.2),
                  color: fraudScoreColor,
                  border: `2px solid ${fraudScoreColor}`,
                  fontWeight: 700,
                  fontSize: '0.875rem',
                  minWidth: 70,
                  boxShadow: fraudScore > 200 ? `0 0 15px ${alpha(fraudScoreColor, 0.5)}` : 'none',
                  animation: fraudScore > 250 ? 'pulse 1.5s infinite' : 'none',
                  transition: 'all 0.3s ease',
                  cursor: 'help',
                }}
              />
            </motion.div>
          </Tooltip>
        </Box>
      </Box>
    </motion.div>
  )
}

// Loading skeleton
function DashboardSkeleton() {
  return (
    <Box>
      <Grid container spacing={3} sx={{ mt: 2 }}>
        {[1, 2, 3, 4].map((i) => (
          <Grid item xs={12} sm={6} md={3} key={i}>
            <Skeleton variant="rectangular" height={120} sx={{ borderRadius: 2 }} />
          </Grid>
        ))}
      </Grid>
      <Box sx={{ mt: 3 }}>
        <Skeleton variant="rectangular" height={400} sx={{ borderRadius: 2 }} />
      </Box>
    </Box>
  )
}

function Dashboard() {
  const [loading, setLoading] = useState(true)
  const [stats, setStats] = useState(null)
  const [columnDialogOpen, setColumnDialogOpen] = useState(false)
  const [selectedColumns, setSelectedColumns] = useState({
    solver_precision_score: false,
    calldown_accuracy: false,
    bet_deviance: false,
    tilt_factor: false,
  })
  const [selectedDate, setSelectedDate] = useState('')
  const [dateOptions, setDateOptions] = useState([])
  const [gameType, setGameType] = useState('cash')
  const [aiDialogOpen, setAiDialogOpen] = useState(false)
  const [aiAnalysis, setAiAnalysis] = useState(null)
  const [aiLoading, setAiLoading] = useState(false)
  const [selectedPlayerForAI, setSelectedPlayerForAI] = useState(null)
  const navigate = useNavigate()
  const theme = useTheme()

  const availableColumns = [
    { key: 'solver_precision_score', label: 'Solver Precision Score', description: '% of optimal solver decisions' },
    { key: 'calldown_accuracy', label: 'Calldown Accuracy', description: 'Win rate when calling on river' },
    { key: 'bet_deviance', label: 'Bet Deviance', description: 'How much player deviates from standard sizing' },
    { key: 'tilt_factor', label: 'Tilt Factor', description: 'Performance drop after losses (0-100)' },
  ]

  useEffect(() => {
    fetchDashboardData(selectedDate)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedDate])

  useEffect(() => {
    axios.get('/api/available-dates')
      .then(r => setDateOptions(r.data.dates || []))
      .catch(err => {
        console.error('Failed to fetch available dates:', err)
        setDateOptions([])
      })
  }, [])

  // Handle game type change
  useEffect(() => {
    if (gameType) {
      console.log(`🎮 Game type changed to: ${gameType.toUpperCase()}`)
      // TODO: When backend is ready, fetch data based on game type
      // fetchDashboardData(selectedDate, gameType)
    }
  }, [gameType])

  const fetchDashboardData = async (dateParam = '') => {
    try {
      const url = dateParam ? `/api/dashboard-summary?date=${dateParam}` : '/api/dashboard-summary'
      const response = await axios.get(url)
      setStats(response.data)
    } catch (error) {
      console.error('Could not fetch dashboard data:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleColumnToggle = (column) => {
    setSelectedColumns(prev => ({
      ...prev,
      [column]: !prev[column]
    }))
  }

  const handleColumnsApply = () => {
    setColumnDialogOpen(false)
  }

  const handlePlayerClick = useCallback((playerId, nickname) => {
    const playerName = nickname || playerId
    navigate(`/hands?player=${encodeURIComponent(playerName)}`)
  }, [navigate])

  // AI Analysis functions
  const analyzePlayer = async (playerData) => {
    console.log('Analyzing player:', playerData)
    setAiLoading(true)
    try {
      const response = await axios.post('/api/ai/analyze-player', playerData)
      console.log('AI response:', response.data)
      
      if (response.data.status === 'success') {
        setAiAnalysis({
          type: 'single',
          data: response.data
        })
        setAiDialogOpen(true)
      } else {
        console.error('AI analysis failed:', response.data.error)
        alert(`AI Analysis failed: ${response.data.error}`)
      }
    } catch (error) {
      console.error('AI analysis error:', error)
      alert('Failed to analyze player. Check if AI service is configured.')
    } finally {
      setAiLoading(false)
    }
  }

  const analyzeTopPlayers = async () => {
    if (!stats?.top_players || stats.top_players.length === 0) {
      alert('No players available to analyze')
      return
    }

    setAiLoading(true)
    try {
      // Send ALL players (up to 25) for comprehensive analysis
      const response = await axios.post('/api/ai/analyze-table', {
        players: stats.top_players,  // Send all players, not just top 5
        max_players: 25  // Updated to analyze up to 25 players
      })
      
      if (response.data.status === 'success') {
        setAiAnalysis({
          type: 'multiple',
          data: response.data
        })
        setAiDialogOpen(true)
      } else {
        console.error('AI analysis failed:', response.data.error)
        alert(`AI Analysis failed: ${response.data.error}`)
      }
    } catch (error) {
      console.error('AI analysis error:', error)
      alert('Failed to analyze players. Check if AI service is configured.')
    } finally {
      setAiLoading(false)
    }
  }

  const checkAIStatus = async () => {
    try {
      const response = await axios.get('/api/ai/status')
      return response.data.available
    } catch (error) {
      console.error('AI status check failed:', error)
      return false
    }
  }

  if (loading) {
    return <DashboardSkeleton />
  }

  // Calculate fraud detection metrics
  const suspiciousPlayers = stats?.top_players?.filter(p => 
    (p.avg_j_score && p.avg_j_score < 30) || 
    (p.winrate_bb100 && p.winrate_bb100 < -20)
  ).length || 0

  const avgWinrate = stats?.top_players?.reduce((acc, p) => acc + (p.winrate_bb100 || 0), 0) / (stats?.top_players?.length || 1) || 0

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
          Fraud Detection Dashboard
        </Typography>
        <Typography variant="subtitle1" sx={{ color: 'text.secondary', mb: 3 }}>
          Real-time poker analytics and anomaly detection
        </Typography>
      </motion.div>

      {/* ── Date selector ───────────────────────────────────── */}
      <motion.div
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.5, delay: 0.2 }}
      >
        <Box sx={{ 
          my: 3, 
          display: 'flex', 
          gap: 3, 
          alignItems: 'center',
          flexWrap: 'wrap'
        }}>
          {/* Date Selector with enhanced styling */}
          <Box sx={{ position: 'relative' }}>
            <Autocomplete
              options={[''].concat(dateOptions)}
              getOptionLabel={(o) => (o === '' ? '📅 Today (live)' : `📅 ${o}`)}
              sx={{ 
                width: 280,
                '& .MuiOutlinedInput-root': {
                  background: 'linear-gradient(135deg, rgba(0, 212, 255, 0.1) 0%, rgba(0, 212, 255, 0.05) 100%)',
                  backdropFilter: 'blur(10px)',
                  border: '1px solid rgba(0, 212, 255, 0.3)',
                  transition: 'all 0.3s ease',
                  '&:hover': {
                    border: '1px solid rgba(0, 212, 255, 0.5)',
                    boxShadow: '0 0 20px rgba(0, 212, 255, 0.2)',
                  },
                  '&.Mui-focused': {
                    border: '1px solid rgba(0, 212, 255, 0.7)',
                    boxShadow: '0 0 30px rgba(0, 212, 255, 0.3)',
                  }
                },
                '& .MuiAutocomplete-popupIndicator': {
                  color: '#00d4ff',
                },
                '& .MuiAutocomplete-clearIndicator': {
                  color: '#00d4ff',
                }
              }}
              value={selectedDate}
              onChange={(_, v) => setSelectedDate(v || '')}
              renderInput={(params) => (
                <TextField 
                  {...params} 
                  id="dashboard-date" 
                  name="date" 
                  label="Select Date" 
                  size="small"
                  InputProps={{
                    ...params.InputProps,
                    startAdornment: (
                      <CalendarIcon sx={{ 
                        color: '#00d4ff', 
                        mr: 1,
                        animation: 'pulse 2s infinite' 
                      }} />
                    ),
                  }}
                  sx={{
                    '& label': {
                      color: '#00d4ff',
                    },
                    '& label.Mui-focused': {
                      color: '#00d4ff',
                    },
                  }}
                />
              )}
            />
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
              style={{
                position: 'absolute',
                top: -10,
                right: -10,
                width: 20,
                height: 20,
                borderRadius: '50%',
                background: 'linear-gradient(135deg, #00d4ff 0%, #00ff88 100%)',
                opacity: 0.5,
                filter: 'blur(8px)',
              }}
            />
          </Box>

          {/* Game Type Toggle */}
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5, delay: 0.3 }}
          >
            <ToggleButtonGroup
              value={gameType}
              exclusive
              onChange={(e, newType) => newType && setGameType(newType)}
              sx={{
                background: 'rgba(17, 24, 39, 0.8)',
                backdropFilter: 'blur(10px)',
                border: '1px solid rgba(0, 212, 255, 0.3)',
                borderRadius: 2,
                overflow: 'hidden',
                '& .MuiToggleButton-root': {
                  color: '#fff',
                  border: 'none',
                  px: 3,
                  py: 1,
                  transition: 'all 0.3s ease',
                  '&:hover': {
                    background: 'rgba(0, 212, 255, 0.1)',
                  },
                  '&.Mui-selected': {
                    background: 'linear-gradient(135deg, rgba(0, 212, 255, 0.3) 0%, rgba(0, 212, 255, 0.1) 100%)',
                    color: '#00d4ff',
                    boxShadow: '0 0 20px rgba(0, 212, 255, 0.4)',
                    '&:hover': {
                      background: 'linear-gradient(135deg, rgba(0, 212, 255, 0.4) 0%, rgba(0, 212, 255, 0.2) 100%)',
                    }
                  }
                }
              }}
            >
              <ToggleButton value="cash">
                <CashIcon sx={{ mr: 1, fontSize: 20 }} />
                <Typography variant="button" sx={{ fontWeight: 600 }}>
                  CASH
                </Typography>
              </ToggleButton>
              <ToggleButton value="mtt">
                <TournamentIcon sx={{ mr: 1, fontSize: 20 }} />
                <Typography variant="button" sx={{ fontWeight: 600 }}>
                  MTT
                </Typography>
              </ToggleButton>
            </ToggleButtonGroup>
          </motion.div>

          {/* Live indicator */}
          {selectedDate === '' && (
            <motion.div
              initial={{ opacity: 0, scale: 0 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.5, delay: 0.4 }}
            >
              <Chip
                label="LIVE"
                size="small"
                sx={{
                  background: 'linear-gradient(135deg, #00ff88 0%, #00d4ff 100%)',
                  color: '#000',
                  fontWeight: 700,
                  px: 2,
                  animation: 'pulse 1.5s infinite',
                  boxShadow: '0 0 20px rgba(0, 255, 136, 0.5)',
                }}
              />
            </motion.div>
          )}
        </Box>
      </motion.div>

      {/* Add pulse animation to styles */}
      <style>
        {`
          @keyframes pulse {
            0% {
              transform: scale(1);
              opacity: 1;
            }
            50% {
              transform: scale(1.05);
              opacity: 0.8;
            }
            100% {
              transform: scale(1);
              opacity: 1;
            }
          }
        `}
      </style>

      <Grid container spacing={3} sx={{ mt: 2 }}>
        <Grid item xs={12} sm={6} md={4}>
          <StatCard
            title="Total Players Analyzed"
            value={stats?.total_players || 0}
            icon={<PeopleIcon sx={{ fontSize: 40 }} />}
            color="#00d4ff"
            delay={0}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={4}>
          <StatCard
            title="Hands Processed"
            value={stats?.total_hands || 0}
            icon={<CasinoIcon sx={{ fontSize: 40 }} />}
            color="#00ff88"
            delay={0.1}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={4}>
          <StatCard
            title="Suspicious Activity"
            value={suspiciousPlayers}
            icon={<WarningIcon sx={{ fontSize: 40 }} />}
            color="#ff4757"
            delay={0.2}
            danger={true}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={6}>
          <StatCard
            title="Avg Preflop Score"
            value={stats?.avg_preflop_score || 0}
            icon={<TrendingUpIcon sx={{ fontSize: 40 }} />}
            color="#a55eea"
            delay={0.3}
            suffix=""
          />
        </Grid>
        <Grid item xs={12} sm={6} md={6}>
          <StatCard
            title="Avg Postflop Score"
            value={stats?.avg_postflop_score || 0}
            icon={<TrendingUpIcon sx={{ fontSize: 40 }} />}
            color="#45aaf2"
            delay={0.4}
            suffix=""
          />
        </Grid>
      </Grid>

      <Grid container spacing={3} sx={{ mt: 3 }}>
        <Grid item xs={12}>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.4 }}
          >
            <Paper 
              sx={{ 
                p: 3,
                background: 'linear-gradient(135deg, rgba(17, 24, 39, 0.9) 0%, rgba(17, 24, 39, 0.7) 100%)',
                backdropFilter: 'blur(10px)',
                border: '1px solid rgba(255, 255, 255, 0.05)',
                position: 'relative',
                overflow: 'hidden',
              }}
            >
              <Box display="flex" alignItems="center" justifyContent="space-between" mb={3}>
                <Box display="flex" alignItems="center" gap={2}>
                  <ShieldIcon sx={{ color: '#00d4ff', fontSize: 28 }} />
                  <Box>
                    <Typography variant="h6" sx={{ fontWeight: 600 }}>
                      Player Risk Assessment
                    </Typography>
                  </Box>
                </Box>
                <Box display="flex" gap={1}>
                  <Button
                    variant="outlined"
                    startIcon={<AnalyzeIcon />}
                    onClick={analyzeTopPlayers}
                    disabled={aiLoading}
                    sx={{
                      color: '#00ff88',
                      borderColor: '#00ff88',
                      '&:hover': {
                        borderColor: '#00ff88',
                        backgroundColor: alpha('#00ff88', 0.1),
                      }
                    }}
                  >
                    {aiLoading ? 'Analyzing...' : 'AI Fraud Detection'}
                  </Button>
                  <IconButton 
                    onClick={() => setColumnDialogOpen(true)}
                    size="small"
                    sx={{
                      color: '#00d4ff',
                      '&:hover': {
                        backgroundColor: alpha('#00d4ff', 0.1),
                      }
                    }}
                  >
                    <SettingsIcon />
                  </IconButton>
                </Box>
              </Box>

              {/* Virtual Table Header */}
              <Box
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  px: 3,
                  py: 2,
                  borderBottom: '2px solid rgba(0, 212, 255, 0.3)',
                  backgroundColor: alpha('#00d4ff', 0.05),
                  overflowX: 'auto',
                  position: 'relative',
                  '&::-webkit-scrollbar': {
                    height: 6,
                  },
                  '&::-webkit-scrollbar-thumb': {
                    backgroundColor: 'rgba(0, 212, 255, 0.3)',
                    borderRadius: 3,
                  },
                }}
              >
                <Box flex="0 0 40px" sx={{ mr: 2 }} />
                <Box flex="1 1 150px">
                  <Typography variant="caption" sx={{ fontWeight: 600, color: '#00d4ff' }}>
                    PLAYER
                  </Typography>
                </Box>
                <Box flex="0 0 40px">
                  <Typography variant="caption" sx={{ fontWeight: 600, color: '#00d4ff' }}>
                    AI
                  </Typography>
                </Box>
                <Box flex="0 0 100px" sx={{ textAlign: 'right' }}>
                  <Typography variant="caption" sx={{ fontWeight: 600, color: '#00d4ff' }}>
                    HANDS
                  </Typography>
                </Box>
                <Box flex="0 0 100px" sx={{ textAlign: 'right' }}>
                  <Typography variant="caption" sx={{ fontWeight: 600, color: '#00d4ff' }}>
                    WIN RATE
                  </Typography>
                </Box>
                <Box flex="0 0 80px" sx={{ textAlign: 'right' }}>
                  <Typography variant="caption" sx={{ fontWeight: 600, color: '#00d4ff' }}>
                    VPIP
                  </Typography>
                </Box>
                <Box flex="0 0 80px" sx={{ textAlign: 'right' }}>
                  <Typography variant="caption" sx={{ fontWeight: 600, color: '#00d4ff' }}>
                    PFR
                  </Typography>
                </Box>
                <Box flex="0 0 80px" sx={{ textAlign: 'right' }}>
                  <Typography variant="caption" sx={{ fontWeight: 600, color: '#00d4ff' }}>
                    J-SCORE
                  </Typography>
                </Box>
                <Box flex="0 0 80px" sx={{ textAlign: 'center' }}>
                  <Typography variant="caption" sx={{ fontWeight: 600, color: '#00d4ff' }}>
                    PREFLOP
                  </Typography>
                </Box>
                <Box flex="0 0 80px" sx={{ textAlign: 'center' }}>
                  <Typography variant="caption" sx={{ fontWeight: 600, color: '#00d4ff' }}>
                    POSTFLOP
                  </Typography>
                </Box>
                {!Object.values(selectedColumns).some(v => v) && (
                  <Box flex="0 0 80px" sx={{ textAlign: 'right' }}>
                    <Typography variant="caption" sx={{ fontWeight: 600, color: '#00d4ff' }}>
                      RISK LEVEL
                    </Typography>
                  </Box>
                )}
                
                {/* Extra column headers */}
                {selectedColumns.solver_precision_score && (
                  <Box flex="0 0 80px" sx={{ textAlign: 'center' }}>
                    <Typography variant="caption" sx={{ fontWeight: 600, color: '#00d4ff' }}>
                      SOLVER %
                    </Typography>
                  </Box>
                )}
                
                {selectedColumns.calldown_accuracy && (
                  <Box flex="0 0 80px" sx={{ textAlign: 'center' }}>
                    <Typography variant="caption" sx={{ fontWeight: 600, color: '#00d4ff' }}>
                      CALL ACC
                    </Typography>
                  </Box>
                )}
                
                {selectedColumns.bet_deviance && (
                  <Box flex="0 0 80px" sx={{ textAlign: 'center' }}>
                    <Typography variant="caption" sx={{ fontWeight: 600, color: '#00d4ff' }}>
                      BET DEV
                    </Typography>
                  </Box>
                )}
                
                {selectedColumns.tilt_factor && (
                  <Box flex="0 0 80px" sx={{ textAlign: 'center' }}>
                    <Typography variant="caption" sx={{ fontWeight: 600, color: '#00d4ff' }}>
                      TILT
                    </Typography>
                  </Box>
                )}
                
                {/* Fraud Score Header - Always visible */}
                <Box flex="0 0 100px" sx={{ 
                  textAlign: 'center',
                  borderLeft: '2px solid rgba(255, 71, 87, 0.3)',
                  pl: 1,
                  background: `linear-gradient(90deg, 
                    transparent 0%, 
                    ${alpha('#ff4757', 0.05)} 50%, 
                    transparent 100%)`,
                }}>
                  <Tooltip 
                    title="Sum of all scores: Preflop + Postflop + Selected columns" 
                    placement="top"
                    arrow
                  >
                    <Typography variant="caption" sx={{ 
                      fontWeight: 700, 
                      color: '#ff4757',
                      fontSize: '0.75rem',
                      cursor: 'help',
                    }}>
                      FRAUD SCORE
                    </Typography>
                  </Tooltip>
                </Box>
              </Box>

              {/* Virtual Table Body */}
              {stats?.top_players && stats.top_players.length > 0 ? (
                <Box sx={{ 
                  position: 'relative',
                  overflow: 'hidden',
                }}>
                  <List
                    height={600}
                    itemCount={stats.top_players.length}
                    itemSize={64}
                    width="100%"
                    itemData={{ 
                      players: stats.top_players, 
                      handlePlayerClick,
                      selectedColumns,
                      analyzePlayer
                    }}
                    style={{
                      overflowX: 'auto',
                    }}
                  >
                    {VirtualRow}
                  </List>
                </Box>
              ) : (
                <Box sx={{ p: 4, textAlign: 'center' }}>
                  <Typography variant="body2" color="text.secondary">
                    No player data available. Check database connection.
                  </Typography>
                </Box>
              )}
            </Paper>
          </motion.div>
        </Grid>
      </Grid>

      <Dialog 
        open={columnDialogOpen} 
        onClose={() => setColumnDialogOpen(false)}
        maxWidth="sm"
        fullWidth
        PaperProps={{
          sx: {
            background: '#111827',
            border: '1px solid rgba(0, 212, 255, 0.3)',
          }
        }}
      >
        <DialogTitle>Customize Table Columns</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            Select additional columns to display
          </Typography>
          <FormGroup>
            {availableColumns.map(column => (
              <Box key={column.key} sx={{ mb: 2 }}>
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={selectedColumns[column.key]}
                      onChange={() => handleColumnToggle(column.key)}
                      sx={{
                        color: '#00d4ff',
                        '&.Mui-checked': {
                          color: '#00d4ff',
                        },
                      }}
                    />
                  }
                  label={
                    <Box>
                      <Typography variant="body1">{column.label}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        {column.description}
                      </Typography>
                    </Box>
                  }
                />
              </Box>
            ))}
          </FormGroup>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setColumnDialogOpen(false)}>
            Cancel
          </Button>
          <Button onClick={handleColumnsApply} variant="contained">
            Apply
          </Button>
        </DialogActions>
      </Dialog>

      {/* AI Analysis Dialog */}
      <Dialog 
        open={aiDialogOpen} 
        onClose={() => setAiDialogOpen(false)}
        maxWidth="md"
        fullWidth
        PaperProps={{
          sx: {
            background: '#111827',
            border: '1px solid rgba(0, 255, 136, 0.3)',
          }
        }}
      >
        <DialogTitle sx={{ 
          display: 'flex', 
          alignItems: 'center', 
          gap: 1,
          borderBottom: '1px solid rgba(0, 255, 136, 0.2)',
        }}>
          <AIIcon sx={{ color: '#00ff88' }} />
          <Typography variant="h6">
            AI Analysis {aiAnalysis?.type === 'single' ? '- Player Report' : '- Fraud Detection Report'}
          </Typography>
        </DialogTitle>
        <DialogContent sx={{ mt: 2 }}>
          {aiAnalysis?.type === 'single' && aiAnalysis.data.analysis && (
            <Box>
              <Typography variant="h6" sx={{ mb: 2, color: '#00d4ff' }}>
                {aiAnalysis.data.player_name} ({aiAnalysis.data.total_hands} hands)
              </Typography>
              
              <Box sx={{ mb: 3 }}>
                <Typography variant="subtitle2" sx={{ color: '#00ff88', mb: 1 }}>
                  Playing Style
                </Typography>
                <Typography variant="body2" sx={{ mb: 2 }}>
                  {typeof aiAnalysis.data.analysis.playing_style === 'string' 
                    ? aiAnalysis.data.analysis.playing_style 
                    : JSON.stringify(aiAnalysis.data.analysis.playing_style)}
                </Typography>
              </Box>

              <Grid container spacing={2}>
                <Grid item xs={12} md={6}>
                  <Paper sx={{ p: 2, background: alpha('#00ff88', 0.05), border: '1px solid rgba(0, 255, 136, 0.2)' }}>
                    <Typography variant="subtitle2" sx={{ color: '#00ff88', mb: 1 }}>
                      Strengths
                    </Typography>
                    <Typography variant="body2">
                      {typeof aiAnalysis.data.analysis.strengths === 'string'
                        ? aiAnalysis.data.analysis.strengths
                        : JSON.stringify(aiAnalysis.data.analysis.strengths)}
                    </Typography>
                  </Paper>
                </Grid>
                <Grid item xs={12} md={6}>
                  <Paper sx={{ p: 2, background: alpha('#ff4757', 0.05), border: '1px solid rgba(255, 71, 87, 0.2)' }}>
                    <Typography variant="subtitle2" sx={{ color: '#ff4757', mb: 1 }}>
                      Weaknesses
                    </Typography>
                    <Typography variant="body2">
                      {typeof aiAnalysis.data.analysis.weaknesses === 'string'
                        ? aiAnalysis.data.analysis.weaknesses
                        : JSON.stringify(aiAnalysis.data.analysis.weaknesses)}
                    </Typography>
                  </Paper>
                </Grid>
              </Grid>

              <Box sx={{ mt: 3 }}>
                <Typography variant="subtitle2" sx={{ color: '#00d4ff', mb: 1 }}>
                  Fraud Risk Score: {aiAnalysis.data.analysis.fraud_risk || 0}/100
                </Typography>
                <LinearProgress 
                  variant="determinate" 
                  value={Number(aiAnalysis.data.analysis.fraud_risk) || 0} 
                  sx={{
                    height: 10,
                    borderRadius: 5,
                    backgroundColor: alpha('#fff', 0.1),
                    '& .MuiLinearProgress-bar': {
                      backgroundColor: (Number(aiAnalysis.data.analysis.fraud_risk) || 0) > 70 ? '#ff4757' : 
                                      (Number(aiAnalysis.data.analysis.fraud_risk) || 0) > 40 ? '#ffa502' : '#00ff88',
                      borderRadius: 5,
                    }
                  }}
                />
              </Box>

              <Box sx={{ mt: 3 }}>
                <Typography variant="subtitle2" sx={{ color: '#a55eea', mb: 1 }}>
                  Recommendations
                </Typography>
                <Typography variant="body2">
                  {typeof aiAnalysis.data.analysis.recommendations === 'string'
                    ? aiAnalysis.data.analysis.recommendations
                    : JSON.stringify(aiAnalysis.data.analysis.recommendations)}
                </Typography>
              </Box>

              {aiAnalysis.data.analysis.red_flags && (
                <Box sx={{ mt: 3 }}>
                  <Typography variant="subtitle2" sx={{ color: '#ff4757', mb: 1 }}>
                    ⚠️ Red Flags
                  </Typography>
                  <Typography variant="body2">
                    {typeof aiAnalysis.data.analysis.red_flags === 'string'
                      ? aiAnalysis.data.analysis.red_flags
                      : JSON.stringify(aiAnalysis.data.analysis.red_flags)}
                  </Typography>
                </Box>
              )}
            </Box>
          )}

          {aiAnalysis?.type === 'multiple' && aiAnalysis.data.analysis && (
            <Box>
              <Typography variant="body2" sx={{ mb: 3, color: 'text.secondary' }}>
                Analyzed {aiAnalysis.data.players_analyzed} players for fraud detection and anomalies
              </Typography>

              <Box sx={{ mb: 3 }}>
                <Typography variant="subtitle2" sx={{ color: '#ff4757', mb: 1 }}>
                  🚨 Anomaly Detection
                </Typography>
                <Typography variant="body2" sx={{ whiteSpace: 'pre-line' }}>
                  {typeof aiAnalysis.data.analysis.anomalies === 'string'
                    ? aiAnalysis.data.analysis.anomalies
                    : JSON.stringify(aiAnalysis.data.analysis.anomalies)}
                </Typography>
              </Box>

              <Box sx={{ mb: 3, p: 2, background: alpha('#ff4757', 0.1), border: '1px solid rgba(255, 71, 87, 0.3)', borderRadius: 1 }}>
                <Typography variant="subtitle2" sx={{ color: '#ff4757', mb: 1 }}>
                  🤖 Bot Indicators
                </Typography>
                <Typography variant="body2" sx={{ whiteSpace: 'pre-line' }}>
                  {typeof aiAnalysis.data.analysis.bot_indicators === 'string'
                    ? aiAnalysis.data.analysis.bot_indicators
                    : JSON.stringify(aiAnalysis.data.analysis.bot_indicators)}
                </Typography>
              </Box>

              <Box sx={{ mb: 3 }}>
                <Typography variant="subtitle2" sx={{ color: '#ffa502', mb: 1 }}>
                  📊 Statistical Outliers
                </Typography>
                <Typography variant="body2" sx={{ whiteSpace: 'pre-line' }}>
                  {typeof aiAnalysis.data.analysis.outliers === 'string'
                    ? aiAnalysis.data.analysis.outliers
                    : JSON.stringify(aiAnalysis.data.analysis.outliers)}
                </Typography>
              </Box>

              <Box sx={{ mb: 3 }}>
                <Typography variant="subtitle2" sx={{ color: '#00d4ff', mb: 1 }}>
                  🔍 Suspicious Patterns
                </Typography>
                <Typography variant="body2" sx={{ whiteSpace: 'pre-line' }}>
                  {typeof aiAnalysis.data.analysis.suspicious_patterns === 'string'
                    ? aiAnalysis.data.analysis.suspicious_patterns
                    : JSON.stringify(aiAnalysis.data.analysis.suspicious_patterns)}
                </Typography>
              </Box>

              <Box sx={{ mt: 3, p: 2, background: alpha('#ff0040', 0.1), border: '2px solid rgba(255, 0, 64, 0.5)', borderRadius: 1 }}>
                <Typography variant="subtitle2" sx={{ color: '#ff0040', mb: 1, fontWeight: 700 }}>
                  ⚠️ TOP 5 MOST SUSPICIOUS PLAYERS
                </Typography>
                <Typography variant="body2" sx={{ whiteSpace: 'pre-line', fontWeight: 500 }}>
                  {typeof aiAnalysis.data.analysis.top_suspicious_players === 'string'
                    ? aiAnalysis.data.analysis.top_suspicious_players
                    : JSON.stringify(aiAnalysis.data.analysis.top_suspicious_players)}
                </Typography>
              </Box>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAiDialogOpen(false)} variant="contained">
            Close
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default Dashboard 