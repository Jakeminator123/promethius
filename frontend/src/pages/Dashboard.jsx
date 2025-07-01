import React, { useState, useEffect } from 'react'
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
} from '@mui/material'
import {
  People as PeopleIcon,
  Casino as CasinoIcon,
  TrendingUp as TrendingUpIcon,
  EmojiEvents as TrophyIcon,
  Settings as SettingsIcon,
} from '@mui/icons-material'
import axios from 'axios'

function StatCard({ title, value, icon, color }) {
  return (
    <Card>
      <CardContent>
        <Box display="flex" alignItems="center" justifyContent="space-between">
          <Box>
            <Typography color="textSecondary" gutterBottom variant="h6">
              {title}
            </Typography>
            <Typography variant="h4">
              {value}
            </Typography>
          </Box>
          <Box sx={{ color: color || 'primary.main' }}>
            {icon}
          </Box>
        </Box>
      </CardContent>
    </Card>
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

  const handleColumnToggle = (column) => {
    setSelectedColumns(prev => ({
      ...prev,
      [column]: !prev[column]
    }))
  }

  const handleColumnsApply = () => {
    setColumnDialogOpen(false)
    // TODO: Refetch data with selected columns
  }

  const handlePlayerClick = (playerId, nickname) => {
    // Navigate to hands page with player parameter
    const playerName = nickname || playerId
    navigate(`/hands?player=${encodeURIComponent(playerName)}`)
  }

  if (loading) {
    return <LinearProgress />
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Dashboard
      </Typography>
      <Typography variant="subtitle1" color="text.secondary" gutterBottom>
        Poker Statistics Overview
      </Typography>

      <Grid container spacing={3} sx={{ mt: 2 }}>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Total Players"
            value={stats?.total_players || 0}
            icon={<PeopleIcon sx={{ fontSize: 40 }} />}
            color="primary.main"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Hands Played"
            value={stats?.total_hands || 0}
            icon={<CasinoIcon sx={{ fontSize: 40 }} />}
            color="success.main"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Average VPIP"
            value={`${stats?.avg_vpip || 0}%`}
            icon={<TrendingUpIcon sx={{ fontSize: 40 }} />}
            color="warning.main"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Average PFR"
            value={`${stats?.avg_pfr || 0}%`}
            icon={<TrophyIcon sx={{ fontSize: 40 }} />}
            color="info.main"
          />
        </Grid>
      </Grid>

      <Grid container spacing={3} sx={{ mt: 3 }}>
        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
              <Typography variant="h6">
                Top 25 Players (Most Hands)
              </Typography>
              <IconButton 
                onClick={() => setColumnDialogOpen(true)}
                size="small"
                title="Customize columns"
              >
                <SettingsIcon />
              </IconButton>
            </Box>
            {stats?.top_players && stats.top_players.length > 0 ? (
              <TableContainer>
                <Table size="small">
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
                      {selectedColumns.solver_precision_score && <TableCell align="right">Solver Precision</TableCell>}
                      {selectedColumns.calldown_accuracy && <TableCell align="right">Calldown Accuracy</TableCell>}
                      {selectedColumns.bet_deviance && <TableCell align="right">Bet Deviance</TableCell>}
                      {selectedColumns.tilt_deviance && <TableCell align="right">Tilt Deviance</TableCell>}
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {stats.top_players.map((player, index) => (
                      <TableRow key={player.player_id} hover>
                        <TableCell>
                          <Box display="flex" alignItems="center" gap={1}>
                            {index < 3 && <TrophyIcon sx={{ fontSize: 16, color: index === 0 ? 'gold' : index === 1 ? 'silver' : '#cd7f32' }} />}
                            <Typography 
                              variant="body2" 
                              sx={{ 
                                cursor: 'pointer', 
                                '&:hover': { 
                                  textDecoration: 'underline',
                                  color: 'primary.main'
                                }
                              }}
                              onClick={() => handlePlayerClick(player.player_id, player.nickname)}
                            >
                              {player.nickname || player.player_id}
                            </Typography>
                          </Box>
                        </TableCell>
                        <TableCell align="right">{player.total_hands}</TableCell>
                        <TableCell align="right">
                          <Chip 
                            label={(player.winrate_bb100 || 0).toFixed(2)} 
                            size="small"
                            color={player.winrate_bb100 > 0 ? 'success' : 'error'}
                          />
                        </TableCell>
                        <TableCell align="right">{(player.vpip || 0).toFixed(1)}</TableCell>
                        <TableCell align="right">{(player.pfr || 0).toFixed(1)}</TableCell>
                        <TableCell align="right">
                          {player.avg_preflop_score !== null && player.avg_preflop_score !== undefined ? (
                            <Chip 
                              label={player.avg_preflop_score.toFixed(1)} 
                              size="small"
                              color={player.avg_preflop_score > 70 ? 'success' : player.avg_preflop_score > 50 ? 'warning' : 'error'}
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
                              color={player.avg_postflop_score > 70 ? 'success' : player.avg_postflop_score > 50 ? 'warning' : 'error'}
                            />
                          ) : (
                            <Typography variant="body2" color="text.secondary">-</Typography>
                          )}
                        </TableCell>
                        <TableCell align="right">
                          {player.avg_j_score !== null && player.avg_j_score !== undefined ? (
                            <Chip 
                              label={player.avg_j_score.toFixed(1)} 
                              size="small"
                              color={player.avg_j_score > 50 ? 'primary' : 'default'}
                            />
                          ) : (
                            <Typography variant="body2" color="text.secondary">-</Typography>
                          )}
                        </TableCell>
                        {selectedColumns.solver_precision_score && (
                          <TableCell align="right">
                            {player.solver_precision_score !== null && player.solver_precision_score !== undefined ? (
                              <Chip 
                                label={player.solver_precision_score.toFixed(1)} 
                                size="small"
                                color={player.solver_precision_score > 70 ? 'success' : player.solver_precision_score > 50 ? 'warning' : 'error'}
                              />
                            ) : (
                              <Typography variant="body2" color="text.secondary">-</Typography>
                            )}
                          </TableCell>
                        )}
                        {selectedColumns.calldown_accuracy && (
                          <TableCell align="right">
                            {player.calldown_accuracy !== null && player.calldown_accuracy !== undefined ? (
                              <Chip 
                                label={player.calldown_accuracy} 
                                size="small"
                                color={player.calldown_accuracy > 60 ? 'success' : player.calldown_accuracy > 45 ? 'warning' : 'error'}
                              />
                            ) : (
                              <Typography variant="body2" color="text.secondary">-</Typography>
                            )}
                          </TableCell>
                        )}
                        {selectedColumns.bet_deviance && (
                          <TableCell align="right">
                            {player.bet_deviance !== null && player.bet_deviance !== undefined ? (
                              <Chip 
                                label={player.bet_deviance} 
                                size="small"
                                color={player.bet_deviance < 20 ? 'default' : player.bet_deviance < 40 ? 'warning' : 'error'}
                              />
                            ) : (
                              <Typography variant="body2" color="text.secondary">-</Typography>
                            )}
                          </TableCell>
                        )}
                        {selectedColumns.tilt_deviance && (
                          <TableCell align="right">
                            {player.tilt_factor !== null && player.tilt_factor !== undefined ? (
                              <Chip 
                                label={player.tilt_factor} 
                                size="small"
                                color={player.tilt_factor < 10 ? 'success' : player.tilt_factor < 25 ? 'warning' : 'error'}
                              />
                            ) : (
                              <Typography variant="body2" color="text.secondary">-</Typography>
                            )}
                          </TableCell>
                        )}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            ) : (
              <Typography variant="body2" color="text.secondary">
                No data available. Check database connection.
              </Typography>
            )}
          </Paper>
        </Grid>
      </Grid>

      <Dialog 
        open={columnDialogOpen} 
        onClose={() => setColumnDialogOpen(false)}
        maxWidth="sm"
        fullWidth
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