import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
import cmocean, sys
from netCDF4 import Dataset
from mpl_toolkits.basemap import Basemap
import PlotTools
from matplotlib.colors import LogNorm
from matplotlib.colors import ListedColormap

# The purpose of this post-processing script is to read in the results
#   from a series of filterings and produce images of the
#   band-filtered kinetic energy.
# A major underlying assumption is that the grid is unchanged
#   between the filterings so that subtraction etc.
#   is trivial.

source = Dataset('input.nc', 'r')

fp = 'filter_output.nc'
results = Dataset(fp, 'r')

R_earth = 6371e3
D2R     = np.pi / 180
R2D     = 180 / np.pi
eps     = 1e-10

# Create cmap for mask data
ref_cmap = cmocean.cm.gray
mask_cmap = ref_cmap(np.arange(ref_cmap.N))
mask_cmap[:,-1] = np.linspace(1, 0, ref_cmap.N)
mask_cmap = ListedColormap(mask_cmap)

# Get the grid from the first filter
latitude  = results.variables['latitude'][:] * R2D
longitude = results.variables['longitude'][:] * R2D
scales    = results.variables['scale'][:]
depth     = results.variables['depth'][:]
time      = results.variables['time'][:]
mask      = results.variables['mask'][:]

num_scales = len(scales)

dlat = (latitude[1]  - latitude[0] ) * D2R
dlon = (longitude[1] - longitude[0]) * D2R
LON, LAT = np.meshgrid(longitude * D2R, latitude * D2R)
dAreas = R_earth**2 * np.cos(LAT) * dlat * dlon

u_r   = results.variables['u_r'  ][:, 0, 0, :, :]
u_lon = results.variables['u_lon'][:, 0, 0, :, :]
u_lat = results.variables['u_lat'][:, 0, 0, :, :]

KE = 0.5 * ( u_r**2 + u_lon**2 + u_lat**2 )

uo = source.variables['uo'][0, 0, :, :]
vo = source.variables['vo'][0, 0, :, :]
Full_KE = 0.5 * (uo**2 + vo**2)

KE_sum_tmp = np.sum( np.sum(KE, axis=0) * mask * dAreas )
KE_orig_tmp = np.sum( Full_KE * mask * dAreas )
print("Lost {0:.3g}% of KE!".format(100 - 100*KE_sum_tmp/KE_orig_tmp))

# Some parameters for plotting
map_settings = PlotTools.MapSettings(longitude, latitude)

meridians = np.round(np.linspace(longitude.min(), longitude.max(), 5))
parallels = np.round(np.linspace(latitude.min(),  latitude.max(),  5))

cbar_props = dict(pad = 0.1, shrink = 0.85, orientation = 'vertical')
gridspec_props = dict(wspace = 0.05, hspace = 0.07, left = 0.04, right = 0.96, bottom = 0.04, top = 0.94)


##
## Begin Plotting
##

## First plot: straight KE binning

# Initialize figure
fig, axes = plt.subplots(num_scales+1, 1,
        sharex=True, sharey=True, 
        gridspec_kw = gridspec_props,
        figsize=(6,4*(num_scales+1)))

# Plot each band
for ii in range(num_scales+1):
    
    if (ii == num_scales):
        to_plot = Full_KE - 0.5 * (   np.sum(u_r,   axis=0)**2 
                                    + np.sum(u_lat, axis=0)**2 
                                    + np.sum(u_lon, axis=0)**2 )
    else:
        to_plot = KE[ii,:,:]
    to_plot = np.ma.masked_where(mask==0, to_plot)

    m  = Basemap(ax = axes[ii], **map_settings)

    CV  = np.nanmax(np.abs(to_plot))
    if (CV == 0):
        CV = 1
    KE_min = np.min(to_plot)
    if (KE_min < 0) :
        print("min(KE) = {0:.4g} < 0!".format(KE_min), ii)
        qm = m.pcolormesh(LON*R2D, LAT*R2D, to_plot, cmap='cmo.balance', vmin = -CV, vmax = CV, latlon = True)
    else:
        qm = m.pcolormesh(LON*R2D, LAT*R2D, to_plot, cmap='cmo.amp', vmin = 0, vmax = CV, latlon = True)
    
    cbar = plt.colorbar(qm, ax = axes[ii], **cbar_props)
    PlotTools.ScientificCbar(cbar, units='')

    # Add coastlines and lat/lon lines
    m.drawcoastlines(linewidth=0.1)
    m.drawparallels(parallels, linewidth=0.5, labels=[0,0,0,0], color='g')
    m.drawmeridians(meridians, linewidth=0.5, labels=[0,0,0,0], color='g')
    m.pcolormesh(LON*R2D, LAT*R2D, mask, vmin=-1, vmax=1, cmap=mask_cmap, latlon=True)

    # Also contour the KE for interests sake
    m.contour(LON*R2D, LAT*R2D, Full_KE, 
            levels = np.array([0, 0.025, 0.1, 0.2]) * np.max(Full_KE * mask),
            cmap='cmo.algae', latlon=True, linewidths=0.2)
        
    if (ii == 0):
        axes[ii].set_ylabel('Below {0:0.1f} km'.format(scales[0] / 1e3))
    elif (ii == num_scales):
        axes[ii].set_ylabel('Orig - bandsum')
    elif (ii == num_scales - 1):
        axes[ii].set_ylabel('Above {0:0.1f} km'.format(scales[ii-1] / 1e3))
    else:
        axes[ii].set_ylabel('{0:.1f} to {1:0.1f} km'.format(scales[ii-1] / 1e3, scales[ii] / 1e3))
        
    
plt.savefig('Figures/KE_band_filter_from_vel.png', dpi=500)
plt.close()

## KE dichotomies

# Initialize figure
fig, axes = plt.subplots(num_scales-1, 3,
        sharex=True, sharey=True, 
        gridspec_kw = gridspec_props,
        figsize=(12, 4*(num_scales-1)))

# Plot each band
for ii in range(num_scales-1):
    
    to_plot_below = 0.5 * (   np.sum(u_r[  :ii+1, :,:], axis=0)**2 
                            + np.sum(u_lat[:ii+1, :,:], axis=0)**2 
                            + np.sum(u_lon[:ii+1, :,:], axis=0)**2 )
    to_plot_above = 0.5 * (   np.sum(u_r[   ii+1:,:,:], axis=0)**2 
                            + np.sum(u_lat[ ii+1:,:,:], axis=0)**2 
                            + np.sum(u_lon[ ii+1:,:,:], axis=0)**2 )
    missing = Full_KE - (to_plot_below + to_plot_above)

    to_plot_below = np.ma.masked_where(mask==0, to_plot_below)
    to_plot_above = np.ma.masked_where(mask==0, to_plot_above)
    missing       = np.ma.masked_where(mask==0, missing)

    m_a = Basemap(ax = axes[ii,0], **map_settings)
    m_b = Basemap(ax = axes[ii,1], **map_settings)
    m_m = Basemap(ax = axes[ii,2], **map_settings)

    CV_a = np.nanmax(np.abs(to_plot_above))
    CV_b = np.nanmax(np.abs(to_plot_below))
    CV_m = np.nanmax(np.abs(missing))

    vmax = max(CV_a, CV_b, CV_m)
    vmin = 10**(np.log10(vmax) - 3)


    qm_a = m_a.pcolormesh(LON*R2D, LAT*R2D, to_plot_above, cmap='cmo.amp', 
            latlon = True, norm=LogNorm(vmin=vmin, vmax=vmax))

    qm_b = m_b.pcolormesh(LON*R2D, LAT*R2D, to_plot_below, cmap='cmo.amp', 
            latlon = True, norm=LogNorm(vmin=vmin, vmax=vmax))

    qm_m = m_m.pcolormesh(LON*R2D, LAT*R2D, missing, cmap='cmo.amp', 
            latlon = True, norm=LogNorm(vmin=vmin, vmax=vmax))

    cbar = plt.colorbar(qm_b, ax = axes[ii,:], **cbar_props)
    #PlotTools.ScientificCbar(cbar_b, units='')

    # Add coastlines and lat/lon lines
    for m in [m_a, m_b, m_m]:
        m.drawcoastlines(linewidth=0.1)
        m.drawparallels(parallels, linewidth=0.5, labels=[0,0,0,0], color='g')
        m.drawmeridians(meridians, linewidth=0.5, labels=[0,0,0,0], color='g')
        m.pcolormesh(LON*R2D, LAT*R2D, mask, vmin=-1, vmax=1, cmap=mask_cmap, latlon=True)

    axes[ii,0].set_ylabel('{0:.1f} km'.format(scales[ii] / 1e3))
        
axes[0,0].set_title('Coarse $(>l)$')
axes[0,1].set_title('Fine $(<l)$')
axes[0,2].set_title('Missing')

plt.savefig('Figures/KE_dichotomies_from_vels.png', dpi=500)
plt.close()

