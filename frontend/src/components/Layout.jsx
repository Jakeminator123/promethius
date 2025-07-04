import React from 'react'
import { Outlet, Link, useLocation } from 'react-router-dom'
import {
  Box,
  Drawer,
  AppBar,
  Toolbar,
  List,
  Typography,
  Divider,
  IconButton,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Container,
  alpha,
} from '@mui/material'
import {
  Menu as MenuIcon,
  Dashboard as DashboardIcon,
  Shield as ShieldIcon,
  Search as SearchIcon,
  QueryStats as StatsIcon,
  Logout as LogoutIcon,
  Security as SecurityIcon,
  BarChart as ChartIcon,
} from '@mui/icons-material'

const drawerWidth = 280

function Layout({ onLogout }) {
  const location = useLocation()
  const [mobileOpen, setMobileOpen] = React.useState(false)

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen)
  }
  
  const handleDrawerClose = () => {
    setMobileOpen(false)
    // Move focus back to menu button when drawer closes
    document.querySelector('[aria-label="open drawer"]')?.focus()
  }

  const menuItems = [
    { text: 'Fraud Detection Dashboard', icon: <ShieldIcon />, path: '/' },
    { text: 'Hand Analysis', icon: <SearchIcon />, path: '/hands' },
    { text: 'Player Segmentation', icon: <StatsIcon />, path: '/advanced-comparison' },
    { text: 'Betting Patterns', icon: <ChartIcon />, path: '/betting-analysis' },
  ]

  const drawer = (
    <Box
      sx={{
        height: '100%',
        background: 'linear-gradient(180deg, #0a0e1a 0%, #111827 100%)',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <Toolbar
        sx={{
          px: 3,
          py: 3,
          borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <SecurityIcon sx={{ color: '#00d4ff', fontSize: 32 }} />
          <Box>
            <Typography
              variant="h6"
              noWrap
              sx={{
                background: 'linear-gradient(135deg, #00d4ff 0%, #00ff88 100%)',
                backgroundClip: 'text',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                fontWeight: 700,
              }}
            >
              PokerGuard AI
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Anti-Fraud Analytics
            </Typography>
          </Box>
        </Box>
      </Toolbar>
      
      <List sx={{ px: 2, py: 2, flexGrow: 1 }}>
        {menuItems.map((item) => {
          const isActive = location.pathname === item.path
          return (
            <ListItem key={item.text} disablePadding sx={{ mb: 1 }}>
              <ListItemButton
                component={Link}
                to={item.path}
                sx={{
                  borderRadius: 2,
                  px: 2,
                  py: 1.5,
                  background: isActive
                    ? 'linear-gradient(135deg, rgba(0, 212, 255, 0.15) 0%, rgba(0, 212, 255, 0.05) 100%)'
                    : 'transparent',
                  border: isActive
                    ? '1px solid rgba(0, 212, 255, 0.3)'
                    : '1px solid transparent',
                  '&:hover': {
                    background: 'rgba(0, 212, 255, 0.05)',
                    border: '1px solid rgba(0, 212, 255, 0.2)',
                  },
                  transition: 'all 0.3s ease',
                }}
              >
                <ListItemIcon
                  sx={{
                    color: isActive ? '#00d4ff' : 'text.secondary',
                    minWidth: 40,
                  }}
                >
                  {item.icon}
                </ListItemIcon>
                <ListItemText
                  primary={item.text}
                  primaryTypographyProps={{
                    fontSize: '0.9rem',
                    fontWeight: isActive ? 600 : 400,
                    color: isActive ? '#00d4ff' : 'text.primary',
                  }}
                />
              </ListItemButton>
            </ListItem>
          )
        })}
      </List>
      
      <Divider sx={{ borderColor: 'rgba(255, 255, 255, 0.05)' }} />
      
      <List sx={{ px: 2, py: 2 }}>
        <ListItem disablePadding>
          <ListItemButton
            onClick={onLogout}
            sx={{
              borderRadius: 2,
              px: 2,
              py: 1.5,
              '&:hover': {
                background: 'rgba(255, 71, 87, 0.1)',
                '& .MuiListItemIcon-root': {
                  color: '#ff4757',
                },
              },
              transition: 'all 0.3s ease',
            }}
          >
            <ListItemIcon sx={{ minWidth: 40 }}>
              <LogoutIcon />
            </ListItemIcon>
            <ListItemText
              primary="Sign Out"
              primaryTypographyProps={{
                fontSize: '0.9rem',
              }}
            />
          </ListItemButton>
        </ListItem>
      </List>
    </Box>
  )

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh', bgcolor: 'background.default' }}>
      <AppBar
        position="fixed"
        sx={{
          width: { sm: `calc(100% - ${drawerWidth}px)` },
          ml: { sm: `${drawerWidth}px` },
          background: alpha('#111827', 0.8),
          backdropFilter: 'blur(10px)',
          borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
          boxShadow: 'none',
        }}
      >
        <Toolbar>
          <IconButton
            color="inherit"
            aria-label="open drawer"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ mr: 2, display: { sm: 'none' } }}
          >
            <MenuIcon />
          </IconButton>
          <Typography variant="h6" noWrap component="div" sx={{ fontWeight: 600 }}>
            {menuItems.find(item => item.path === location.pathname)?.text || 'PokerGuard AI'}
          </Typography>
        </Toolbar>
      </AppBar>

      <Box
        component="nav"
        sx={{ width: { sm: drawerWidth }, flexShrink: { sm: 0 } }}
      >
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={handleDrawerClose}
          ModalProps={{
            keepMounted: true
          }}
          sx={{
            display: { xs: 'block', sm: 'none' },
            '& .MuiDrawer-paper': {
              boxSizing: 'border-box',
              width: drawerWidth,
              backgroundColor: '#0a0e1a',
              borderRight: '1px solid rgba(255, 255, 255, 0.05)',
            },
          }}
        >
          {drawer}
        </Drawer>
        <Drawer
          variant="permanent"
          sx={{
            display: { xs: 'none', sm: 'block' },
            '& .MuiDrawer-paper': {
              boxSizing: 'border-box',
              width: drawerWidth,
              backgroundColor: '#0a0e1a',
              borderRight: '1px solid rgba(255, 255, 255, 0.05)',
            },
          }}
          open
        >
          {drawer}
        </Drawer>
      </Box>

      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          width: { sm: `calc(100% - ${drawerWidth}px)` },
          background: 'radial-gradient(ellipse at top right, rgba(0, 212, 255, 0.05) 0%, transparent 50%)',
          minHeight: '100vh',
        }}
      >
        <Toolbar />
        <Container maxWidth="xl">
          <Outlet />
        </Container>
      </Box>
    </Box>
  )
}

export default Layout 