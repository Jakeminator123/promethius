import React, { useState, useEffect, useMemo } from 'react'
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
  Avatar,
  alpha,
  useTheme,
  CircularProgress,
  Skeleton,
} from '@mui/material'
import {
  People as PeopleIcon,
  Casino as CasinoIcon,
  TrendingUp as TrendingUpIcon,
  EmojiEvents as TrophyIcon,
  Settings as SettingsIcon,
  Timeline as TimelineIcon,
  Speed as SpeedIcon,
  Psychology as PsychologyIcon,
  LocalFireDepartment as FireIcon,
  Star as StarIcon,
  ArrowUpward as ArrowUpIcon,
  ArrowDownward as ArrowDownIcon,
} from '@mui/icons-material'
import { PieChart, Pie, Cell, ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip } from 'recharts'
import axios from 'axios'

// Enhanced StatCard without problematic animations
function StatCard({ title, value, icon, color, trend, trendValue, delay = 0 }) {
  const theme = useTheme()
  
  return (
    <Card
      sx={{
        position: 'relative',
        overflow: 'hidden',
        height: '140px',
        background: `linear-gradient(135deg, ${alpha(color, 0.1)} 0%, ${alpha(color, 0.05)} 100%)`,
        border: `1px solid ${alpha(color, 0.2)}`,
        transition: 'all 0.3s ease',
        '&:hover': {
          background: `linear-gradient(135deg, ${alpha(color, 0.15)} 0%, ${alpha(color, 0.08)} 100%)`,
          border: `1px solid ${alpha(color, 0.4)}`,
          transform: 'translateY(-2px)',
        },
      }}
    >
      <CardContent sx={{ height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
        <Box display="flex" alignItems="flex-start" justifyContent="space-between">
          <Box>
            <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 500, mb: 1 }}>
              {title}
            </Typography>
            <Typography 
              variant="h4" 
              sx={{ 
                fontWeight: 700,
                color: color,
                fontSize: { xs: '1.8rem', md: '2.2rem' }
              }}
            >
              {value}
            </Typography>
          </Box>
          <Avatar 
            sx={{ 
              background: `linear-gradient(135deg, ${color} 0%, ${alpha(color, 0.8)} 100%)`,
              color: theme.palette.mode === 'dark' ? '#000' : '#fff',
              width: 56,
              height: 56,
            }}
          >
            {icon}
          </Avatar>
        </Box>
        
        {trend && trendValue && (
          <Box display="flex" alignItems="center" mt={1}>
            {trend === 'up' ? (
              <ArrowUpIcon sx={{ color: theme.palette.success.main, fontSize: 18, mr: 0.5 }} />
            ) : (
              <ArrowDownIcon sx={{ color: theme.palette.error.main, fontSize: 18, mr: 0.5 }} />
            )}
            <Typography 
              variant="caption" 
              sx={{ 
                color: trend === 'up' ? theme.palette.success.main : theme.palette.error.main,
                fontWeight: 600 
              }}
            >
              {trendValue}% from last month
            </Typography>
          </Box>
        )}
      </CardContent>
    </Card>
  )
}

// Enhanced Player Row without problematic animations
function PlayerRow({ player, index, onPlayerClick }) {
  const theme = useTheme()
  
  const getScoreColor = (score, thresholds = [70, 50]) => {
    if (score > thresholds[0]) return theme.palette.success.main
    if (score > thresholds[1]) return theme.palette.warning.main
    return theme.palette.error.main
  }

  const getMedalColor = (index) => {
    if (index === 0) return '#FFD700' // Gold
    if (index === 1) return '#C0C0C0' // Silver
    if (index === 2) return '#CD7F32' // Bronze
    return theme.palette.primary.main
  }

  return (
    <TableRow 
      hover 
      sx={{ 
        cursor: 'pointer',
        transition: 'all 0.2s ease',
        '&:hover': {
          background: alpha(theme.palette.primary.main, 0.08),
          transform: 'translateX(4px)',
        },
      }}
      onClick={() => onPlayerClick(player.player_id, player.nickname)}
    >
      <TableCell>
        <Box display="flex" alignItems="center" gap={2}>
          <Avatar 
            sx={{ 
              width: 32, 
              height: 32,
              background: `linear-gradient(135deg, ${getMedalColor(index)} 0%, ${alpha(getMedalColor(index), 0.7)} 100%)`,
              color: '#000',
              fontWeight: 700,
              fontSize: '0.8rem'
            }}
          >
            {index < 3 ? <TrophyIcon sx={{ fontSize: 16 }} /> : index + 1}
          </Avatar>
          <Box>
            <Typography 
              variant="body2" 
              sx={{ 
                fontWeight: 600,
                color: theme.palette.text.primary,
                '&:hover': { 
                  color: theme.palette.primary.main
                }
              }}
            >
              {player.nickname || player.player_id}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              #{index + 1} player
            </Typography>
          </Box>
        </Box>
      </TableCell>
      
      <TableCell align="right">
        <Typography variant="body2" fontWeight={500}>
          {player.total_hands?.toLocaleString()}
        </Typography>
      </TableCell>
      
      <TableCell align="right">
        <Chip 
          label={(player.winrate_bb100 || 0).toFixed(2)} 
          size="small"
          sx={{
            background: player.winrate_bb100 > 0 
              ? `linear-gradient(135deg, ${theme.palette.success.main} 0%, ${alpha(theme.palette.success.main, 0.8)} 100%)`
              : `linear-gradient(135deg, ${theme.palette.error.main} 0%, ${alpha(theme.palette.error.main, 0.8)} 100%)`,
            color: '#000',
            fontWeight: 600,
          }}
        />
      </TableCell>
      
      <TableCell align="right">
        <Typography variant="body2" fontWeight={500}>
          {(player.vpip || 0).toFixed(1)}%
        </Typography>
      </TableCell>
      
      <TableCell align="right">
        <Typography variant="body2" fontWeight={500}>
          {(player.pfr || 0).toFixed(1)}%
        </Typography>
      </TableCell>
      
      <TableCell align="right">
        {player.avg_preflop_score !== null && player.avg_preflop_score !== undefined ? (
          <Chip 
            label={player.avg_preflop_score.toFixed(1)} 
            size="small"
            sx={{
              background: `linear-gradient(135deg, ${getScoreColor(player.avg_preflop_score)} 0%, ${alpha(getScoreColor(player.avg_preflop_score), 0.8)} 100%)`,
              color: '#000',
              fontWeight: 600,
            }}
          />
        ) : (
          <Typography variant="body2" color="text.secondary">-</Typography>
        )}
      </TableCell>
      
      <TableCell align="right">
        {player.avg_postflop_score !== null && player.avg_postflop_score !== undefined ? (
          <Chip 
            label={player.avg_postflop_score.toFixed(1)} 
            size="small"
            sx={{
              background: `linear-gradient(135deg, ${getScoreColor(player.avg_postflop_score)} 0%, ${alpha(getScoreColor(player.avg_postflop_score), 0.8)} 100%)`,
              color: '#000',
              fontWeight: 600,
            }}
          />
        ) : (
          <Typography variant="body2" color="text.secondary">-</Typography>
        )}
      </TableCell>
      
      <TableCell align="right">
        {player.avg_j_score !== null && player.avg_j_score !== undefined ? (
          <Box display="flex" alignItems="center" justifyContent="flex-end" gap={1}>
            <Chip 
              label={player.avg_j_score.toFixed(1)} 
              size="small"
              sx={{
                background: `linear-gradient(135deg, ${theme.palette.primary.main} 0%, ${alpha(theme.palette.primary.main, 0.8)} 100%)`,
                color: '#000',
                fontWeight: 600,
              }}
            />
            {player.avg_j_score > 55 && <StarIcon sx={{ color: theme.palette.warning.main, fontSize: 16 }} />}
          </Box>
        ) : (
          <Typography variant="body2" color="text.secondary">-</Typography>
        )}
      </TableCell>
    </TableRow>
  )
}

// Simple PieChart for statistics
function StatsPieChart({ data, title }) {
  const theme = useTheme()
  const COLORS = [theme.palette.primary.main, theme.palette.secondary.main, theme.palette.info.main, theme.palette.warning.main]

  return (
    <Paper sx={{ p: 3, height: '300px' }}>
      <Typography variant="h6" gutterBottom sx={{ color: theme.palette.primary.main, fontWeight: 600 }}>
        {title}
      </Typography>
      <ResponsiveContainer width="100%" height="80%">
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            outerRadius={80}
            fill="#8884d8"
            dataKey="value"
            label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip />
        </PieChart>
      </ResponsiveContainer>
    </Paper>
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
    tilt_deviance: false,
  })
  const navigate = useNavigate()
  const theme = useTheme()

  const availableColumns = [
    { key: 'solver_precision_score', label: 'Solver Precision Score' },
    { key: 'calldown_accuracy', label: 'Calldown Accuracy' },
    { key: 'bet_deviance', label: 'Bet Deviance' },
    { key: 'tilt_deviance', label: 'Tilt Deviance' },
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

  // Memoized statistics for charts
  const pieChartData = useMemo(() => {
    if (!stats?.top_players) return []
    
    const highScore = stats.top_players.filter(p => p.avg_j_score > 60).length
    const mediumScore = stats.top_players.filter(p => p.avg_j_score > 40 && p.avg_j_score <= 60).length
    const lowScore = stats.top_players.filter(p => p.avg_j_score <= 40).length
    
    return [
      { name: 'High Skill', value: highScore },
      { name: 'Medium Skill', value: mediumScore },
      { name: 'Low Skill', value: lowScore },
    ]
  }, [stats?.top_players])

  const handleColumnToggle = (column) => {
    setSelectedColumns(prev => ({
      ...prev,
      [column]: !prev[column]
    }))
  }

  const handleColumnsApply = () => {
    setColumnDialogOpen(false)
  }

  const handlePlayerClick = (playerId, nickname) => {
    const playerName = nickname || playerId
    navigate(`/hands?player=${encodeURIComponent(playerName)}`)
  }

  if (loading) {
    return (
      <Box sx={{ p: 3 }}>
        <Skeleton variant="text" height={60} width="40%" sx={{ mb: 2 }} />
        <Skeleton variant="text" height={30} width="60%" sx={{ mb: 4 }} />
        <Grid container spacing={3}>
          {[1, 2, 3, 4].map((i) => (
            <Grid item xs={12} sm={6} md={3} key={i}>
              <Skeleton variant="rectangular" height={140} sx={{ borderRadius: 2 }} />
            </Grid>
          ))}
        </Grid>
      </Box>
    )
  }

  return (
    <Box sx={{ p: { xs: 2, md: 3 } }}>
      <Box mb={4}>
        <Typography 
          variant="h3" 
          gutterBottom 
          sx={{ 
            background: `linear-gradient(135deg, ${theme.palette.primary.main} 0%, ${theme.palette.secondary.main} 100%)`,
            backgroundClip: 'text',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            fontWeight: 700,
            mb: 1
          }}
        >
          Poker Analytics Dashboard
      </Typography>
        <Typography variant="h6" color="text.secondary" sx={{ fontWeight: 400 }}>
          Overview of all players and their performance
      </Typography>
      </Box>

      {/* Statistics cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Total Players"
            value={stats?.total_players?.toLocaleString() || 0}
            icon={<PeopleIcon />}
            color={theme.palette.primary.main}
            trend="up"
            trendValue="12"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Hands Played"
            value={stats?.total_hands?.toLocaleString() || 0}
            icon={<CasinoIcon />}
            color={theme.palette.info.main}
            trend="up"
            trendValue="8"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Average VPIP"
            value={`${(stats?.avg_vpip || 0).toFixed(1)}%`}
            icon={<TrendingUpIcon />}
            color={theme.palette.warning.main}
            trend="down"
            trendValue="3"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Average PFR"
            value={`${(stats?.avg_pfr || 0).toFixed(1)}%`}
            icon={<PsychologyIcon />}
            color={theme.palette.secondary.main}
            trend="up"
            trendValue="5"
          />
        </Grid>
      </Grid>

      {/* Charts and table */}
      <Grid container spacing={3}>
        {/* Main table */}
        <Grid item xs={12} lg={8}>
          <Paper sx={{ p: 3 }}>
            <Box display="flex" alignItems="center" justifyContent="space-between" mb={3}>
              <Box>
                <Typography variant="h5" sx={{ fontWeight: 600, mb: 1 }}>
                  Top 25 Players
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Ranked by number of hands played
              </Typography>
              </Box>
              <IconButton 
                onClick={() => setColumnDialogOpen(true)}
                sx={{ 
                  background: alpha(theme.palette.primary.main, 0.1),
                  '&:hover': {
                    background: alpha(theme.palette.primary.main, 0.2),
                  }
                }}
              >
                <SettingsIcon />
              </IconButton>
            </Box>
            
            {stats?.top_players && stats.top_players.length > 0 ? (
              <TableContainer sx={{ maxHeight: 600 }}>
                <Table stickyHeader>
                  <TableHead>
                    <TableRow>
                      <TableCell>Player</TableCell>
                      <TableCell align="right">Hands</TableCell>
                      <TableCell align="right">Winrate (BB/100)</TableCell>
                      <TableCell align="right">VPIP %</TableCell>
                      <TableCell align="right">PFR %</TableCell>
                      <TableCell align="right">Preflop Score</TableCell>
                      <TableCell align="right">Postflop Score</TableCell>
                      <TableCell align="right">Overall J-Score</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {stats.top_players.slice(0, 25).map((player, index) => (
                      <PlayerRow
                        key={player.player_id}
                        player={player}
                        index={index}
                        onPlayerClick={handlePlayerClick}
                      />
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            ) : (
              <Box 
                display="flex" 
                flexDirection="column" 
                alignItems="center" 
                justifyContent="center" 
                py={8}
              >
                <CircularProgress sx={{ mb: 2 }} />
                <Typography variant="h6" color="text.secondary">
                  {stats?.database_status === 'building' 
                    ? 'Building database...' 
                    : stats?.database_status === 'error'
                    ? 'Database Error'
                    : 'Loading player data...'}
                </Typography>
              <Typography variant="body2" color="text.secondary">
                  {stats?.message || stats?.error_message || 'Scraping and processing poker hands. This may take a few minutes.'}
                </Typography>
                {stats?.database_status === 'building' && (
                  <Typography variant="caption" color="text.secondary" sx={{ mt: 1, textAlign: 'center' }}>
                    Status: Scraping data from API and running analysis scripts<br/>
                    This process can take 5-15 minutes for large datasets
              </Typography>
                )}
              </Box>
            )}
          </Paper>
        </Grid>

        {/* Side panel with charts */}
        <Grid item xs={12} lg={4}>
          <Box display="flex" flexDirection="column" gap={3}>
            {/* Skill distribution */}
            <StatsPieChart
              data={pieChartData}
              title="Skill Distribution"
            />

            {/* Quick stats */}
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom sx={{ color: theme.palette.primary.main, fontWeight: 600 }}>
                Quick Stats
              </Typography>
              <Box display="flex" flexDirection="column" gap={2}>
                <Box display="flex" justifyContent="space-between" alignItems="center">
                  <Typography variant="body2">Total Actions</Typography>
                  <Chip 
                    label={stats?.total_actions?.toLocaleString() || '0'} 
                    size="small" 
                    color="primary" 
                  />
                </Box>
                <Box display="flex" justifyContent="space-between" alignItems="center">
                  <Typography variant="body2">Average J-Score</Typography>
                  <Chip 
                    label={(stats?.avg_j_score || 0).toFixed(1)} 
                    size="small" 
                    color="secondary" 
                  />
                </Box>
                <Box display="flex" justifyContent="space-between" alignItems="center">
                  <Typography variant="body2">Active Players</Typography>
                  <Chip 
                    label={stats?.top_players?.length || 0} 
                    size="small" 
                    color="info" 
                  />
                </Box>
              </Box>
            </Paper>
          </Box>
        </Grid>
      </Grid>

      {/* Dialog for columns */}
      <Dialog 
        open={columnDialogOpen} 
        onClose={() => setColumnDialogOpen(false)}
        maxWidth="sm"
        fullWidth
        PaperProps={{
          sx: {
            background: `linear-gradient(145deg, ${theme.palette.background.paper} 0%, ${alpha(theme.palette.background.paper, 0.9)} 100%)`,
          }
        }}
      >
        <DialogTitle>Customize Table Columns</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            Select up to 4 additional columns to display
          </Typography>
          <FormGroup>
            {availableColumns.map(column => (
              <FormControlLabel
                key={column.key}
                control={
                  <Checkbox
                    checked={selectedColumns[column.key]}
                    onChange={() => handleColumnToggle(column.key)}
                    disabled={
                      !selectedColumns[column.key] && 
                      Object.values(selectedColumns).filter(v => v).length >= 4
                    }
                  />
                }
                label={column.label}
              />
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