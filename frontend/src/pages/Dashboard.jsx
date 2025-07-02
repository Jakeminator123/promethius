import React, { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Grid,
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
  const { players, handlePlayerClick, selectedColumns } = data
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
  const navigate = useNavigate()
  const theme = useTheme()

  const availableColumns = [
    { key: 'solver_precision_score', label: 'Solver Precision Score', description: '% of optimal solver decisions' },
    { key: 'calldown_accuracy', label: 'Calldown Accuracy', description: 'Win rate when calling on river' },
    { key: 'bet_deviance', label: 'Bet Deviance', description: 'How much player deviates from standard sizing' },
    { key: 'tilt_factor', label: 'Tilt Factor', description: 'Performance drop after losses (0-100)' },
  ]

  useEffect(() => {
    fetchDashboardData()
  }, [])

  const fetchDashboardData = async () => {
    try {
      const response = await axios.get('/api/dashboard-summary')
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

              {/* Virtual Table Header */}
              <Box
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  px: 3,
                  py: 2,
                  borderBottom: '2px solid rgba(0, 212, 255, 0.3)',
                  backgroundColor: alpha('#00d4ff', 0.05),
                }}
              >
                <Box flex="0 0 40px" sx={{ mr: 2 }} />
                <Box flex="1 1 150px">
                  <Typography variant="caption" sx={{ fontWeight: 600, color: '#00d4ff' }}>
                    PLAYER
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
              </Box>

              {/* Virtual Table Body */}
              {stats?.top_players && stats.top_players.length > 0 ? (
                <List
                  height={600}
                  itemCount={stats.top_players.length}
                  itemSize={64}
                  width="100%"
                  itemData={{ 
                    players: stats.top_players, 
                    handlePlayerClick,
                    selectedColumns 
                  }}
                >
                  {VirtualRow}
                </List>
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
    </Box>
  )
}

export default Dashboard 