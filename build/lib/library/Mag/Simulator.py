from . import Mag
from . import MathUtils
from . import ProblemSetter
from . import DataIO
import SimPEG.PF as PF
import shapefile
from SimPEG.Utils import mkvc
from scipy.constants import mu_0
from matplotlib import pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
import ipywidgets as widgets
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from scipy.interpolate import griddata, interp1d, RegularGridInterpolator
import scipy.sparse as sp
from scipy.spatial import cKDTree
from scipy.interpolate.interpnd import _ndim_coords_from_arrays
from matplotlib.colors import LightSource, Normalize
from library.graphics import graphics
from matplotlib.ticker import FormatStrFormatter
import matplotlib as mpl
import PIL

def PFSimulator(prism, survey):

    def PFInteract(update, susc, comp, irt, Q, RemInc, RemDec,
                   Profile_npt, Profile_azm, Profile_len,
                   Profile_ctx, Profile_cty):

        # # Get the line extent from the 2D survey for now
        prob = Mag.Problem()
        prob.prism = prism
        prob.survey = survey

        return PlotFwrSim(prob, susc, comp, irt, Q, RemInc, RemDec,
                          Profile_azm, Profile_len, Profile_npt,
                          Profile_ctx, Profile_cty)

    locs = survey.srcField.rxList[0].locs
    xlim = np.asarray([locs[:, 0].min(), locs[:, 0].max()])
    ylim = np.asarray([locs[:, 1].min(), locs[:, 1].max()])

    Lx = xlim[1] - xlim[0]
    Ly = ylim[1] - ylim[0]
    diag = (Lx**2. + Ly**2.)**0.5/2.

    ctx = np.mean(xlim)
    cty = np.mean(ylim)

    out = widgets.interactive(PFInteract,
                              update=widgets.ToggleButton(description='Refresh', value=False),
                              susc=widgets.FloatSlider(min=0, max=2, step=0.001, value=0.1, continuous_update=False),
                              comp=widgets.ToggleButtons(options=['tf', 'bx', 'by', 'bz']),
                              irt=widgets.ToggleButtons(options=['induced', 'remanent',  'total']),
                              Q=widgets.FloatSlider(min=0., max=10, step=1, value=0, continuous_update=False),
                              RemInc=widgets.FloatSlider(min=-90., max=90, step=5, value=0, continuous_update=False),
                              RemDec=widgets.FloatSlider(min=-90., max=90, step=5, value=0, continuous_update=False),
                              Profile_npt=widgets.BoundedFloatText(min=10, max=100, step=1, value=20, continuous_update=False),
                              Profile_azm=widgets.FloatSlider(min=-90, max=90, step=5, value=45., continuous_update=False),
                              Profile_len=widgets.FloatSlider(min=10, max=diag, step=10, value= Ly, continuous_update=False),
                              Profile_ctx=widgets.FloatSlider(value=ctx, min=xlim[0], max=xlim[1], step=0.1, continuous_update=False, color='black'),
                              Profile_cty=widgets.FloatSlider(value=cty, min=ylim[0], max=ylim[1], step=0.1, continuous_update=False, color='black'), )
    return out


def cmaps():
    """
      Return some pre-selected colormaps from matplotlib
    """

    return [
              'viridis', 'plasma', 'magma', 'RdBu_r',
              'Greys_r', 'jet', 'rainbow', 'pink',
               'bone', 'hsv', 'nipy_spectral'
            ]


def PlotFwrSim(prob, susc, comp, irt, Q, rinc, rdec,
               Profile_azm, Profile_len, Profile_npt,
               Profile_ctx, Profile_cty):

    def MagSurvey2D(x, y, data, Profile_ctx, Profile_cty, Profile_azm,
                    Profile_len, Profile_npt,
                    fig=None, ax=None,
                    vmin=None, vmax=None, pred=None):

        # Get the line extent from the 2D survey for now
        Profile_azm /= 180./np.pi
        Profile_len /= 2.*0.98

        dx = np.cos(-Profile_azm)*Profile_len
        dy = np.sin(-Profile_azm)*Profile_len

        a = [Profile_ctx - dx, Profile_cty - dy]
        b = [Profile_ctx + dx, Profile_cty + dy]

        return plotMagSurvey2D(x, y,
                               data, a, b, Profile_npt,
                               fig=fig, ax=ax,
                               vmin=vmin, vmax=vmax, pred=pred)

    def MagSurveyProfile(survey, Profile_ctx, Profile_cty, Profile_azm,
                         Profile_len, Profile_npt,
                         data=None, fig=None, ax=None):

        # Get the line extent from the 2D survey for now
        Profile_azm /= 180./np.pi
        Profile_len /= 2.*0.98

        dx = np.cos(-Profile_azm)*Profile_len
        dy = np.sin(-Profile_azm)*Profile_len

        a = [Profile_ctx - dx, Profile_cty - dy]
        b = [Profile_ctx + dx, Profile_cty + dy]

        xyz = survey.srcField.rxList[0].locs
        dobs = survey.dobs

        return plotProfile2D(xyz[:, 0], xyz[:, 1], [dobs, data], a, b, Profile_npt,
                             fig=fig, ax=ax, ylabel='nT')

    survey = prob.survey
    rxLoc = survey.srcField.rxList[0].locs
    prob.Q, prob.rinc, prob.rdec = Q, rinc, rdec
    prob.uType, prob.mType = comp, irt
    prob.susc = susc

    # Compute fields from prism
    fields = prob.fields()

    dpred = np.zeros_like(fields[0])
    for b in fields:
        dpred += b

    vmin = survey.dobs.min()
    vmax = survey.dobs.max()
    rxLoc = survey.srcField.rxList[0].locs
    x, y = rxLoc[:, 0], rxLoc[:, 1]

    f = plt.figure(figsize=(8, 8))

    ax0 = plt.subplot(1, 2, 1)
    MagSurvey2D(x, y, survey.dobs, Profile_ctx, Profile_cty, Profile_azm,
                Profile_len, Profile_npt, fig=f, ax=ax0, pred=dpred,
                vmin=survey.dobs.min(), vmax=survey.dobs.max())

    ax0 = plt.subplot(1, 2, 2)
    MagSurvey2D(x, y, dpred, Profile_ctx, Profile_cty, Profile_azm,
                Profile_len, Profile_npt, fig=f, ax=ax0, pred=dpred,
                vmin=survey.dobs.min(), vmax=survey.dobs.max())

    f = plt.figure(figsize=(12, 5))
    ax2 = plt.subplot()
    MagSurveyProfile(survey, Profile_ctx, Profile_cty, Profile_azm,
                     Profile_len, Profile_npt, data=dpred, fig=f, ax=ax2)

    plt.show()


def ViewMagSurveyWidget(survey):

    def MagSurvey2D(East, North, Azimuth, Length, Sampling, ):

        # Get the line extent from the 2D survey for now
        ColorMap = "RdBu_r"
        Azimuth = np.deg2rad((450 - Azimuth) % 360)
        Length /= 2.*0.98
        a = [East - np.cos(Azimuth)*Length, North - np.sin(Azimuth)*Length]
        b = [East + np.cos(Azimuth)*Length, North + np.sin(Azimuth)*Length]

        fig = plt.figure(figsize=(10, 6))
        ax1 = plt.subplot(1, 2, 1)

        plotMagSurvey2D(
         xLoc, yLoc, data, a, b, Sampling,
         fig=fig, ax=ax1, cmap=ColorMap, marker=False
        )

        # if Profile:
        ax2 = plt.subplot(1, 2, 2)
        plotProfile2D(xLoc, yLoc, data, a, b, Sampling,
                      fig=fig, ax=ax2, ylabel='nT')

        # ax2.set_aspect(0.5)
        pos = ax2.get_position()
        ax2.set_position([pos.x0, pos.y0+0.25, pos.width*2.0, pos.height*0.5])
        ax2.set_title('A', loc='left', fontsize=14)
        ax2.set_title("A'", loc='right', fontsize=14)

        plt.show()
        return survey

    # Calculate the original map extents
    if isinstance(survey, DataIO.dataGrid):
        xLoc = survey.hx
        yLoc = survey.hy
        data = survey.values
    else:
        xLoc = survey.srcField.rxList[0].locs[:, 0]
        yLoc = survey.srcField.rxList[0].locs[:, 1]
        data = survey.dobs

    Lx = xLoc.max() - xLoc.min()
    Ly = yLoc.max() - yLoc.min()
    diag = (Lx**2. + Ly**2.)**0.5

    cntr = [np.mean(xLoc), np.mean(yLoc)]

    out = widgets.interactive(
        MagSurvey2D,
        East=widgets.FloatSlider(min=cntr[0]-Lx, max=cntr[0]+Lx, step=10, value=cntr[0],continuous_update=False),
        North=widgets.FloatSlider(min=cntr[1]-Ly, max=cntr[1]+Ly, step=10, value=cntr[1],continuous_update=False),
        Azimuth=widgets.FloatSlider(min=0, max=180, step=5, value=90, continuous_update=False),
        Length=widgets.FloatSlider(min=20, max=diag, step=20, value=diag/2., continuous_update=False),
        Sampling=widgets.BoundedFloatText(min=10, max=1000, step=5, value=100, continuous_update=False)
        # ColorMap=widgets.Dropdown(
        #           options=cmaps(),
        #           value='RdBu_r',
        #           description='ColorMap',
        #           disabled=False,
        #         )
    )

    return out


def plotMagSurvey2D(x, y, data, a, b, npts, pred=None, marker=True,
                    fig=None, ax=None, vmin=None, vmax=None,
                    cmap='RdBu_r', equalizeHist='HistEqualized'):
    """
    Plot the data and line profile inside the spcified limits
    """

    if fig is None:
        fig = plt.figure()

    if ax is None:
        ax = plt.subplot()

    xLine, yLine = linefun(a[0], b[0], a[1], b[1], npts)

    # Use SimPEG.PF ploting function
    fig, im, cbar = plotData2D(x, y, data, fig=fig,  ax=ax,
                         vmin=vmin, vmax=vmax,
                         marker=marker, cmap=cmap,
                         colorbar=False, equalizeHist=equalizeHist)

    ax.plot(xLine, yLine, 'k.', ms=5)
    cbar = plt.colorbar(im, orientation='horizontal')
    cbar.set_label('TMI (nT)')
    ax.text(xLine[0], yLine[0], 'A', fontsize=16, color='k', ha='left')
    ax.text(xLine[-1], yLine[-1], "A'", fontsize=16,
            color='k', ha='right')
    ax.grid(True)

    return


def linefun(x1, x2, y1, y2, nx, tol=1e-3):
    dx = x2-x1
    dy = y2-y1

    if np.abs(dx) < tol:
        y = np.linspace(y1, y2, nx)
        x = np.ones_like(y)*x1
    elif np.abs(dy) < tol:
        x = np.linspace(x1, x2, nx)
        y = np.ones_like(x)*y1
    else:
        x = np.linspace(x1, x2, nx)
        slope = (y2-y1)/(x2-x1)
        y = slope*(x-x1)+y1
    return x, y


def ViewPrism(survey):

    def Prism(update, dx, dy, dz, x0, y0, elev, prism_inc, prism_dec, View_dip, View_azm, View_lim):

        prism = definePrism()
        prism.dx, prism.dy, prism.dz, prism.z0 = dx, dy, dz, elev
        prism.x0, prism.y0 = x0, y0
        prism.pinc, prism.pdec = prism_inc, prism_dec

        # Display the prism and survey points
        plotObj3D([prism], survey, View_dip, View_azm, View_lim)

        return prism

    rxLoc = survey.srcField.rxList[0].locs
    cntr = np.mean(rxLoc[:, :2], axis=0)

    xlim = rxLoc[:, 0].max() - rxLoc[:, 0].min()
    ylim = rxLoc[:, 1].max() - rxLoc[:, 1].min()

    lim = np.max([xlim, ylim])/2.

    out = widgets.interactive(Prism,
                              update=widgets.ToggleButton(description='Refresh', value=False),
                              dx=widgets.FloatSlider(min=.01, max=1000., step=.01, value=lim/4, continuous_update=False),
                              dy=widgets.FloatSlider(min=.01, max=1000., step=.01, value=lim/4, continuous_update=False),
                              dz=widgets.FloatSlider(min=.01, max=1000., step=.01, value=lim/4, continuous_update=False),
                              x0=widgets.FloatSlider(min=cntr[0]-1000, max=cntr[0]+1000, step=1., value=cntr[0], continuous_update=False),
                              y0=widgets.FloatSlider(min=cntr[1]-1000, max=cntr[1]+1000, step=1., value=cntr[1], continuous_update=False),
                              elev=widgets.FloatSlider(min=-1000., max=1000., step=1., value=0., continuous_update=False),
                              prism_inc=(-90., 90., 5.),
                              prism_dec=(-90., 90., 5.),
                              View_dip=widgets.FloatSlider(min=0, max=90, step=1, value=30, continuous_update=False),
                              View_azm=widgets.FloatSlider(min=0, max=360, step=1, value=0, continuous_update=False),
                              View_lim=widgets.FloatSlider(min=1, max=2*lim, step=1, value=lim, continuous_update=False),
                              )

    return out


def plotObj3D(prisms, survey, View_dip, View_azm, View_lim, fig=None, axs=None, title=None, colors=None):

    """
    Plot the prism in 3D
    """

    rxLoc = survey.srcField.rxList[0].locs

    if fig is None:
        fig = plt.figure(figsize=(7, 7))

    if axs is None:
        axs = fig.add_subplot(111, projection='3d')

    if title is not None:
        axs.set_title(title)

    plt.rcParams.update({'font.size': 13})

    cntr = np.mean(rxLoc[:, :2], axis=0)

    axs.set_xlim3d(-View_lim + cntr[0], View_lim + cntr[0])
    axs.set_ylim3d(-View_lim + cntr[1], View_lim + cntr[1])
#     axs.set_zlim3d(depth+np.array(surveyArea[:2]))
    axs.set_zlim3d(rxLoc[:, 2].max()*1.1-View_lim*2, rxLoc[:, 2].max()*1.1)

    if colors is None:
        colors = ['w']*len(prisms)

    for prism, color in zip(prisms, colors):

        x1, x2 = prism.xn[0], prism.xn[1]
        y1, y2 = prism.yn[0], prism.yn[1]
        z1, z2 = prism.zn[0], prism.zn[1]
        pinc, pdec = prism.pinc, prism.pdec

        # Create a rectangular prism, rotate and plot
        block_xyz = np.asarray([[x1, x1, x2, x2, x1, x1, x2, x2],
                               [y1, y2, y2, y1, y1, y2, y2, y1],
                               [z1, z1, z1, z1, z2, z2, z2, z2]])

        xyz = MathUtils.rotate(block_xyz.T, np.r_[prism.xc, prism.yc, prism.zc], pinc, pdec)
        # R = MagUtils.rotationMatrix(pinc, pdec)

        # xyz = R.dot(block_xyz).T

        # Offset the prism to true coordinate
        # offx = prism.xc
        # offy = prism.yc
        # offz = prism.zc

        #print xyz
        # Face 1
        axs.add_collection3d(Poly3DCollection([list(zip(xyz[:4, 0],
                                                   xyz[:4, 1],
                                                   xyz[:4, 2]))]))

        # Face 2
        axs.add_collection3d(Poly3DCollection([list(zip(xyz[4:, 0],
                                                   xyz[4:, 1],
                                                   xyz[4:, 2]))], facecolors=color))

        # Face 3
        axs.add_collection3d(Poly3DCollection([list(zip(xyz[[0, 1, 5, 4], 0],
                                                   xyz[[0, 1, 5, 4], 1],
                                                   xyz[[0, 1, 5, 4], 2]))]))

        # Face 4
        axs.add_collection3d(Poly3DCollection([list(zip(xyz[[3, 2, 6, 7], 0],
                                                   xyz[[3, 2, 6, 7], 1],
                                                   xyz[[3, 2, 6, 7], 2]))]))

       # Face 5
        axs.add_collection3d(Poly3DCollection([list(zip(xyz[[0, 4, 7, 3], 0],
                                                   xyz[[0, 4, 7, 3], 1],
                                                   xyz[[0, 4, 7, 3], 2]))]))

       # Face 6
        axs.add_collection3d(Poly3DCollection([list(zip(xyz[[1, 5, 6, 2], 0],
                                                   xyz[[1, 5, 6, 2], 1],
                                                   xyz[[1, 5, 6, 2], 2]))]))


    axs.set_xlabel('Easting (X; m)')
    axs.set_ylabel('Northing (Y; m)')
    axs.set_zlabel('Depth (Z; m)')

    if survey.dobs is not None:
        color = survey.dobs
    else:
        color = 'k'
    axs.scatter(rxLoc[:, 0], rxLoc[:, 1], zs=rxLoc[:, 2], c=color, s=20, cmap='RdBu_r', zorder=100)

    # Convert from geographic
    azmDeg = (450 - View_azm) % 360 + 180

    axs.view_init(View_dip, azmDeg)
    plt.show()

    return True


class definePrism(object):
    """
        Define a prism and its attributes

        Prism geometry:
            - dx, dy, dz: width, length and height of prism
            - depth : depth to top of prism
            - susc : susceptibility of prism
            - x0, y0 : center of prism in horizontal plane
            - pinc, pdec : inclination and declination of prism
    """

    x0, y0, z0, dx, dy, dz = 0., 0., 0., 1., 1., 1.
    pinc, pdec = 0., 0.


    # Define the nodes of the prism
    @property
    def xn(self):
        xn = np.asarray([-self.dx/2. + self.x0, self.dx/2. + self.x0])

        return xn

    @property
    def yn(self):
        yn = np.asarray([-self.dy/2. + self.y0, self.dy/2. + self.y0])

        return yn

    @property
    def zn(self):
        zn = np.asarray([-self.dz + self.z0, self.z0])

        return zn

    @property
    def xc(self):
        xc = (self.xn[0] + self.xn[1]) / 2.

        return xc

    @property
    def yc(self):
        yc = (self.yn[0] + self.yn[1]) / 2.

        return yc

    @property
    def zc(self):
        zc = (self.zn[0] + self.zn[1]) / 2.

        return zc


def fitline(prism, survey):

    def profiledata(Binc, Bdec, Bigrf, depth,
                    susc, comp, irt, Q, rinc, rdec, update):

        # Get the line extent from the 2D survey for now
        prob = Mag.problem()
        prob.prism = prism.result

        xyzLoc = survey.srcField.rxList[0].locs.copy()
        xyzLoc[:, 2] += depth

        rxLoc = PF.BaseMag.RxObs(xyzLoc)
        srcField = PF.BaseMag.SrcField([rxLoc], param=[Bigrf, Binc, Bdec])
        survey2D = PF.BaseMag.LinearSurvey(srcField)
        survey2D.dobs = survey.dobs
        prob.survey = survey2D

        prob.Q, prob.rinc, prob.rdec = Q, rinc, rdec
        prob.uType, prob.mType = comp, irt
        prob.susc = susc

        # Compute fields from prism
        fields = prob.fields()

        dpred = np.zeros_like(fields[0])
        for b in fields:
            dpred += (b + Bigrf)

        a = np.r_[xyzLoc[:, 0].min(), 0]
        b = np.r_[xyzLoc[:, 0].max(), 0]
        return plotProfile2D(
                  xyzLoc, [survey2D.dobs, dpred], a, b, 10,
                  dType='2D', ylabel='nT',
                )

    Q = widgets.interactive(
        profiledata, Binc=widgets.FloatSlider(min=-90., max=90, step=5, value=90, continuous_update=False),
        Bdec=widgets.FloatSlider(min=-90., max=90, step=5, value=0, continuous_update=False),
        Bigrf=widgets.FloatSlider(min=54000., max=55000, step=10, value=54500, continuous_update=False),
        depth=widgets.FloatSlider(min=0., max=2., step=0.05, value=0.5),
        susc=widgets.FloatSlider(min=0.,  max=800., step=5.,  value=1.),
        comp=widgets.ToggleButtons(options=['tf', 'bx', 'by', 'bz']),
        irt=widgets.ToggleButtons(options=['induced', 'remanent', 'total']),
        Q=widgets.FloatSlider(min=0.,  max=10., step=0.1,  value=0.),
        rinc=widgets.FloatSlider(min=-180.,  max=180., step=1.,  value=0.),
        rdec=widgets.FloatSlider(min=-180.,  max=180., step=1.,  value=0.),
        update=widgets.ToggleButton(description='Refresh', value=False)
    )
    return Q


class MidPointNorm(Normalize):
    """
      Color range normalization based on a mid-point
      Provided from:
      https://stackoverflow.com/questions/7404116/defining-the-midpoint-of-a-colormap-in-matplotlib
    """
    def __init__(self, midpoint=None, vmin=None, vmax=None, clip=False):
        Normalize.__init__(self, vmin, vmax, clip)
        self.midpoint = midpoint

    def __call__(self, value, clip=None):
        if clip is None:
            clip = self.clip

        result, is_scalar = self.process_value(value)

        self.autoscale_None(result)

        if self.midpoint is None:
            self.midpoint = (self.vmin + self.vmax)/2.
        vmin, vmax, midpoint = self.vmin, self.vmax, self.midpoint

        if not (vmin < midpoint < vmax):
            raise ValueError("midpoint must be between maxvalue and minvalue.")
        elif vmin == vmax:
            result.fill(0) # Or should it be all masked? Or 0.5?
        elif vmin > vmax:
            raise ValueError("maxvalue must be bigger than minvalue")
        else:
            vmin = float(vmin)
            vmax = float(vmax)
            if clip:
                mask = np.ma.getmask(result)
                result = np.ma.array(np.clip(result.filled(vmax), vmin, vmax),
                                  mask=mask)

            # ma division is very slow; we can take a shortcut
            resdat = result.data

            # First scale to -1 to 1 range, than to from 0 to 1.
            resdat -= midpoint
            resdat[resdat > 0] /= abs(vmax - midpoint)
            resdat[resdat < 0] /= abs(vmin - midpoint)

            resdat /= 2.
            resdat += 0.5
            result = np.ma.array(resdat, mask=result.mask, copy=False)

        if is_scalar:
            result = result[0]
        return result

    def inverse(self, value):
        if not self.scaled():
            raise ValueError("Not invertible until scaled")
        vmin, vmax, midpoint = self.vmin, self.vmax, self.midpoint

        if cbook.iterable(value):
            val = ma.asarray(value)
            val = 2 * (val-0.5)
            val[val > 0] *= abs(vmax - midpoint)
            val[val < 0] *= abs(vmin - midpoint)
            val += midpoint
            return val
        else:
            val = 2 * (val - 0.5)
            if val < 0:
                return val*abs(vmin-midpoint) + midpoint
            else:
                return val*abs(vmax-midpoint) + midpoint


def plotDataHillside(x, y, z, axs=None, fill=True, contours=25,
                     vmin=None, vmax=None, levels=None, resolution=25,
                     clabel=True, cmap='RdBu_r', ve=1., alpha=0.5, alphaHS=0.5,
                     distMax=1000, midpoint=None, azdeg=315, altdeg=45,
                     equalizeHist='HistEqualized', minCurvature=True, scatterData=None):

    ls = LightSource(azdeg=azdeg, altdeg=altdeg)

    if z.ndim == 1:

        if minCurvature:
            gridCC, d_grid = MathUtils.minCurvatureInterp(
                np.c_[x, y], z,
                vectorX=None, vectorY=None, vectorZ=None, gridSize=resolution,
                tol=1e-5, iterMax=None, method='spline',
            )
            X = gridCC[:, 0].reshape(d_grid.shape, order='F')
            Y = gridCC[:, 1].reshape(d_grid.shape, order='F')

        else:
            npts_x = int((x.max() - x.min())/Resolution)
            npts_y = int((y.max() - y.min())/Resolution)
            # Create grid of points
            vectorX = np.linspace(x.min(), x.max(), npts_x)
            vectorY = np.linspace(y.min(), y.max(), npts_y)

            Y, X = np.meshgrid(vectorY, vectorX)

            d_grid = griddata(np.c_[x, y], z, (X, Y), method='cubic')

        # Remove points beyond treshold
        tree = cKDTree(np.c_[x, y])
        xi = _ndim_coords_from_arrays((X, Y), ndim=2)
        dists, indexes = tree.query(xi)

        # Copy original result but mask missing values with NaNs
        d_grid[dists > distMax] = np.nan

    else:

        X, Y, d_grid = x, y, z

    im, CS = [], []
    if axs is None:
        axs = plt.subplot()

    if fill:

        if vmin is None:
            vmin = np.floor(d_grid[~np.isnan(d_grid)].min())

        if vmax is None:
            vmax = np.ceil(d_grid[~np.isnan(d_grid)].max())

        if equalizeHist == 'HistEqualized':

            subGrid = d_grid[~np.isnan(d_grid)]
            cdf, bins = exposure.cumulative_distribution(
                    subGrid[
                       (subGrid < vmax) *
                       (subGrid > vmin)
                       ].flatten(), nbins=256
            )
            my_cmap = graphics.equalizeColormap(cmap, bins, cdf)
        else:
            my_cmap = cmap

        extent = x.min(), x.max(), y.min(), y.max()
        im = axs.imshow(d_grid, vmin=vmin, vmax=vmax,
                       cmap=my_cmap, clim=[vmin, vmax],
                       alpha=alpha,
                       extent=extent, origin='lower')
        if np.all([alpha != 1, alphaHS != 0]):
            axs.imshow(ls.hillshade(d_grid, vert_exag=ve,
                       dx=resolution, dy=resolution),
                       cmap='gray_r', alpha=alphaHS,
                       extent=extent, origin='lower')

        # clevels = np.linspace(vmin, vmax, contours)
        # im = axs.contourf(
        #     X, Y, d_grid, contours, levels=clevels,
        #     cmap=my_cmap, alpha=alpha
        # )


    if levels is not None:
        CS = axs.contour(
            X, Y, d_grid, levels.shape[0],
            levels=levels, colors='k', linewidths=0.5
        )

        if clabel:
            plt.clabel(CS, inline=1, fontsize=10, fmt='%i')

    if scatterData is not None:
        plt.scatter(
          scatterData['x'], scatterData['y'],
          scatterData['size'], c=scatterData['c'],
          cmap=scatterData['cmap'],
          vmin=scatterData['clim'][0],
          vmax=scatterData['clim'][1]
        )
        axs.set_xlim([extent[0], extent[1]])
        axs.set_ylim([extent[2], extent[3]])
        axs.set_aspect('auto')
    return X, Y, d_grid, im, CS


def plotData2D(x, y, d, title=None,
               vmin=None, vmax=None, contours=None, fig=None, ax=None,
               colorbar=True, marker=True, cmap="RdBu_r",
               equalizeHist='HistEqualized'):
    """ Function plot_obs(rxLoc,d)
    Generate a 2d interpolated plot from scatter points of data

    INPUT
    rxLoc       : Observation locations [x,y,z]
    d           : Data vector

    OUTPUT
    figure()

    Created on Dec, 27th 2015

    @author: dominiquef

    """

    from scipy.interpolate import griddata
    import pylab as plt

    # Plot result
    if fig is None:
        fig = plt.figure()

    if ax is None:
        ax = plt.subplot()

    if d.ndim == 1:
        assert x.shape[0] == d.shape[0], "Data and x locations must be consistant"

        assert y.shape[0] == d.shape[0], "Data and y locations must be consistant"


    plt.sca(ax)
    if marker:
        plt.scatter(x, y, c='k', s=10)

    if d is not None:

        ndv = np.isnan(d) == False
        if (vmin is None):
            vmin = d[ndv].min()

        if (vmax is None):
            vmax = d[ndv].max()

        # If data not a grid, create points evenly sampled
        if d.ndim == 1:
            # Create grid of points
            xGrid = np.linspace(x.min(), x.max(), 100)
            yGrid = np.linspace(y.min(), y.max(), 100)

            X, Y = np.meshgrid(xGrid, yGrid)
            d_grid = griddata(np.c_[x, y], d, (X, Y), method='linear')

        # Already a grid
        else:

            if x.ndim == 1:
                X, Y = np.meshgrid(x, y)
                d_grid = d

            else:
                X, Y, d_grid = x, y, d

        if equalizeHist == 'HistEqualized':
            cdf, bins = exposure.cumulative_distribution(
                d_grid[~np.isnan(d_grid)].flatten(), nbins=256
            )
            my_cmap = graphics.equalizeColormap(cmap, bins, cdf)
        else:

            my_cmap = cmap

        im = plt.imshow(
                d_grid, extent=[x.min(), x.max(), y.min(), y.max()],
                origin='lower', vmin=vmin, vmax=vmax, cmap=my_cmap
              )

        cbar = []
        if colorbar:
            cbar = plt.colorbar(fraction=0.02)

        if contours is None:

            if vmin != vmax:
                plt.contour(X, Y, d_grid, 10, vmin=vmin, vmax=vmax, cmap=my_cmap)
        else:
            plt.contour(X, Y, d_grid, levels=contours, colors='k',
                        vmin=vmin, vmax=vmax)

    if title is not None:
        plt.title(title)

    plt.yticks(rotation='vertical')

    ylabel = np.round(np.linspace(y.min(), y.max(), 5) * 1e-3) * 1e+3
    ax.set_yticklabels(ylabel[1:4], size=12, rotation=90, va='center')
    ax.set_yticks(ylabel[1:4])
    ax.yaxis.set_major_formatter(FormatStrFormatter('%.0f'))
    xlabel = np.round(np.linspace(x.min(), x.max(), 5) * 1e-3) * 1e+3
    ax.set_xticklabels(xlabel[1:4], size=12, va='center')
    ax.set_xticks(xlabel[1:4])
    ax.xaxis.set_major_formatter(FormatStrFormatter('%.0f'))
    ax.set_xlabel('Easting')
    ax.set_ylabel('Northing')
    ax.grid(True)
    ax.set_aspect('equal')
    # plt.gca().set_aspect('equal', adjustable='box')

    return fig, im, cbar


def plotProfile2D(x, y, data, a, b, npts,
                  fig=None, ax=None, plotStr=['b', 'r'],
                  coordinate_system='local',
                  ylabel='Data'):
    """
    Plot the data and line profile inside the spcified limits
    """
    def linefun(x1, x2, y1, y2, nx, tol=1e-3):
        dx = x2-x1
        dy = y2-y1

        if np.abs(dx) <= tol:
            y = np.linspace(y1, y2, nx)
            x = np.ones_like(y)*x1
        elif np.abs(dy) <= tol:
            x = np.linspace(x1, x2, nx)
            y = np.ones_like(x)*y1
        else:
            x = np.linspace(x1, x2, nx)
            slope = (y2-y1)/(x2-x1)
            y = slope*(x-x1)+y1
        return x, y

    if fig is None:
        fig = plt.figure(figsize=(6, 9))

        plt.rcParams.update({'font.size': 14})

    if ax is None:
        ax = plt.subplot()

    xLine, yLine = linefun(a[0], b[0], a[1], b[1], npts)

    ind = (xLine > x.min()) * (xLine < x.max()) * (yLine > y.min()) * (yLine < y.max())

    xLine = xLine[ind]
    yLine = yLine[ind]

    distance = np.sqrt((xLine-a[0])**2.+(yLine-a[1])**2.)
    if coordinate_system == 'xProfile':
        distance += a[0]
    elif coordinate_system == 'yProfile':
        distance += a[1]

    if not isinstance(data, list):
        data = [data]

    for ii, d in enumerate(data):
        if d.ndim == 1:
            dline = griddata(np.c_[x, y], d, (xLine, yLine), method='linear')

        else:
            F = RegularGridInterpolator((x, y), d.T)
            dline = F(np.c_[xLine, yLine])

        # Check for nan
        ind = np.isnan(dline)==False

        if plotStr[ii]:
            ax.plot(distance[ind], dline[ind], plotStr[ii])
        else:
            ax.plot(distance[ind], dline[ind])

    # ax.set_xlim(distance.min(), distance.max())
    ax.set_ylabel(ylabel)
    ax.set_aspect('auto')
    ax.grid(True)
    return ax


def dataHillsideWidget(
    survey, EPSGCode=26909,
    figName='DataHillshade', dpi=300,
    scatterData=None
  ):

    def plotWidget(
            SunAzimuth, SunAngle,
            ColorTransp, HSTransp, vScale,
            Contours, ColorMap, VminVmax, Equalize,
            SaveGeoTiff
         ):

        if SaveGeoTiff:
            fig = plt.figure()
            fig.set_size_inches(9, 9)
            axs = plt.Axes(fig, [0., 0., 1., 1.])
            axs.set_axis_off()
            fig.add_axes(axs)

        else:
            fig = plt.figure(figsize=(9, 9))
            axs = plt.subplot()

        # Add shading
        X, Y, d_grid, im, CS = plotDataHillside(
          xLoc, yLoc, data,
          axs=axs, cmap=ColorMap,
          clabel=False, contours=Contours,
          vmax=VminVmax[1], vmin=VminVmax[0],
          alpha=ColorTransp, alphaHS=HSTransp,
          ve=vScale, azdeg=SunAzimuth, altdeg=SunAngle,
          equalizeHist=Equalize, scatterData=scatterData)

        # Add points at the survey locations
        # plt.scatter(xLoc, yLoc, s=2, c='k')
        if SaveGeoTiff:
            plt.savefig("Output/" + figName + '.png', dpi=dpi)
            plt.close()

            img = np.asarray(PIL.Image.open("Output/" + figName + '.png'))

            DataIO.arrayToRaster(
                img, "Output/" + figName + '.tiff',
                EPSGCode, np.min(X), np.max(X), np.min(Y), np.max(Y), 3
            )

        else:
            axs.set_aspect('equal')
            cbar = plt.colorbar(im, fraction=0.02)
            cbar.set_label('TMI (nT)')

            axs.set_xlabel("Easting (m)", size=14)
            axs.set_ylabel("Northing (m)", size=14)
            axs.grid('on', color='k', linestyle='--')

            if scatterData is not None:
                pos = axs.get_position()
                cbarax = fig.add_axes([pos.x0+0.875, pos.y0+0.225,  pos.width*.025, pos.height*0.4])
                norm = mpl.colors.Normalize(vmin=scatterData['clim'][0], vmax=scatterData['clim'][1])
                cb = mpl.colorbar.ColorbarBase(
                  cbarax, cmap=scatterData['cmap'],
                  norm=norm,
                  orientation="vertical")
                cb.set_label("Depth (m)", size=12)

            plt.show()

    # Calculate the original map extents
    if isinstance(survey, DataIO.dataGrid):
        xLoc = survey.hx
        yLoc = survey.hy
        data = survey.values

    else:
        xLoc = survey.srcField.rxList[0].locs[:, 0]
        yLoc = survey.srcField.rxList[0].locs[:, 1]
        data = survey.dobs

    out = widgets.interactive(plotWidget,
                              SunAzimuth=widgets.FloatSlider(
                                min=0, max=360, step=5, value=90, continuous_update=False),
                              SunAngle=widgets.FloatSlider(min=0, max=90, step=5, value=15, continuous_update=False),
                              ColorTransp=widgets.FloatSlider(
                                min=0, max=1, step=0.05, value=0.9, continuous_update=False),
                              HSTransp=widgets.FloatSlider(
                                min=0, max=1, step=0.05, value=0.50, continuous_update=False),
                              vScale=widgets.FloatSlider(
                                min=1, max=10, step=1., value=5.0, continuous_update=False),
                              Contours=widgets.IntSlider(min=10, max=100, step=10, value=50, continuous_update=False),
                              ColorMap=widgets.Dropdown(
                                  options=cmaps(),
                                  value='RdBu_r',
                                  description='ColorMap',
                                  disabled=False,
                                ),
                              VminVmax=widgets.FloatRangeSlider(
                                    value=[data.min(), data.max()],
                                    min=data.min(),
                                    max=data.max(),
                                    step=1.0,
                                    description='Color Range',
                                    disabled=False,
                                    continuous_update=False,
                                    orientation='horizontal',
                                    readout=True,
                                    readout_format='.1f',
                                ),
                              Equalize=widgets.Dropdown(
                                  options=['Linear', 'HistEqualized'],
                                  value='HistEqualized',
                                  description='Color Normalization',
                                  disabled=False,
                                ),
                              SaveGeoTiff=widgets.ToggleButton(
                                  value=False,
                                  description='Export geoTiff',
                                  disabled=False,
                                  button_style='',
                                  tooltip='Description',
                                  icon='check'
                                )
                              )
    return out


def gridFiltersWidget(
  survey, gridFilter='derivativeX',
  figName=None,
  EPSGCode=26909, dpi=300, scatterData=None):

    def plotWidget(
            SunAzimuth, SunAngle,
            ColorTransp, HSTransp, vScale,
            ColorMap, Filters, SaveGrid
         ):

        if Filters == 'TMI':
            data = survey.values
            vmin, vmax = data.min(), data.max()
            equalizeHist = 'HistEqualized'

        else:
            data = getattr(filters, '{}'.format(Filters))
            vmin, vmax = np.percentile(data, 5), np.percentile(data, 95)
            equalizeHist = 'HistEqualized'

        vScale *= np.abs(survey.values.max() - survey.values.min()) * np.abs(data.max() - data.min())
        plotIt(
            X, Y, data, SunAzimuth, SunAngle,
            ColorTransp, HSTransp, vScale,
            ColorMap, Filters, vmin, vmax, equalizeHist, SaveGrid
        )

    def plotWidgetUpC(
            SunAzimuth, SunAngle,
            ColorTransp, HSTransp, vScale,
            ColorMap, Filters, UpwardDistance, SaveGrid
         ):
        if Filters == 'TMI':
            data = survey.values
            vmin, vmax = data.min(), data.max()

        else:
            data = filters.upwardContinuation(z=UpwardDistance)
            vmin, vmax = data.min(), data.max()

        plotIt(
            X, Y, data, SunAzimuth, SunAngle,
            ColorTransp, HSTransp, vScale,
            ColorMap, Filters, vmin, vmax, 'HistEqualized', SaveGrid
        )

        gridOut = survey
        gridOut.values = data

        return gridOut

    def plotWidgetRTP(
            SunAzimuth, SunAngle,
            ColorTransp, HSTransp, vScale,
            ColorMap, Filters, inc, dec, SaveGrid
         ):
        if Filters == 'TMI':
            data = survey.values
            vmin, vmax = data.min(), data.max()

        else:
            filters._RTP = None
            filters.inc = inc
            filters.dec = dec
            data = filters.RTP
            vmin, vmax = data.min(), data.max()

        plotIt(
            X, Y, data, SunAzimuth, SunAngle,
            ColorTransp, HSTransp, vScale,
            ColorMap, Filters, vmin, vmax, 'HistEqualized', SaveGrid
        )

    def plotIt(
            X, Y, data, SunAzimuth, SunAngle,
            ColorTransp, HSTransp, vScale,
            ColorMap, Filters, vmin, vmax, equalizeHist, SaveGrid
         ):

        if SaveGrid:
            fig = plt.figure()
            fig.set_size_inches(9, 9)
            axs = plt.Axes(fig, [0., 0., 1., 1.])
            axs.set_axis_off()
            fig.add_axes(axs)

        else:

            fig = plt.figure(figsize=(10, 10))
            axs = plt.subplot()

        # Add shading
        X, Y, data, im, CS = plotDataHillside(
            X, Y, data,
            axs=axs, cmap=ColorMap,
            clabel=False, resolution=10,
            vmin=vmin, vmax=vmax, contours=50,
            alpha=ColorTransp, alphaHS=HSTransp,
            ve=vScale, azdeg=SunAzimuth, altdeg=SunAngle,
            equalizeHist=equalizeHist, scatterData=scatterData
        )

        if SaveGrid:

            if figName is None:
              figName = gridFilter

            plt.savefig("Output/" + figName + '.png', dpi=dpi)
            plt.close()

            img = np.asarray(PIL.Image.open("Output/" + figName + '.png'))

            DataIO.arrayToRaster(
                img, "Output/" + figName + '.tiff',
                EPSGCode, np.min(X), np.max(X), np.min(Y), np.max(Y), 3
            )

        else:
            # Add points at the survey locations
            # plt.scatter(xLoc, yLoc, s=2, c='k')
            axs.set_aspect('equal')
            cbar = plt.colorbar(im, fraction=0.02)
            cbar.set_label(gridFilter)

            axs.set_xlabel("Easting (m)", size=14)
            axs.set_ylabel("Northing (m)", size=14)
            axs.grid('on', color='k', linestyle='--')

            if scatterData is not None:
                pos = axs.get_position()
                cbarax = fig.add_axes([pos.x0+0.875, pos.y0+0.225,  pos.width*.025, pos.height*0.4])
                norm = mpl.colors.Normalize(vmin=scatterData['clim'][0], vmax=scatterData['clim'][1])
                cb = mpl.colorbar.ColorbarBase(
                  cbarax, cmap=scatterData['cmap'],
                  norm=norm,
                  orientation="vertical")
                cb.set_label("Depth (m)", size=12)

            plt.show()

    # Calculate the original map extents
    if isinstance(survey, DataIO.dataGrid):
        filters = MathUtils.gridFilter()
        filters.grid = survey.values
        filters.dx = survey.dx
        filters.dy = survey.dy

        X, Y = np.meshgrid(survey.hx, survey.hy)

        data = getattr(filters, '{}'.format(gridFilter))
    else:

        assert isinstance(survey, DataIO.dataGrid), 'Only implemented for grids'

    if gridFilter == 'upwardContinuation':
        out = widgets.interactive(plotWidgetUpC,
                                  SunAzimuth=widgets.FloatSlider(
                                    min=0, max=360, step=5, value=90,
                                    continuous_update=False),
                                  SunAngle=widgets.FloatSlider(
                                    min=0, max=90, step=5, value=15,
                                    continuous_update=False),
                                  ColorTransp=widgets.FloatSlider(
                                    min=0, max=1, step=0.05, value=0.9,
                                    continuous_update=False),
                                  HSTransp=widgets.FloatSlider(
                                    min=0, max=1, step=0.05, value=0.50,
                                    continuous_update=False),
                                  vScale=widgets.FloatSlider(
                                    min=1, max=10, step=1., value=5.0,
                                    continuous_update=False),
                                  ColorMap=widgets.Dropdown(
                                      options=cmaps(),
                                      value='RdBu_r',
                                      description='ColorMap',
                                      disabled=False,
                                    ),
                                  Filters=widgets.Dropdown(
                                      options=[
                                        gridFilter,
                                        'TMI'],
                                      value=gridFilter,
                                      description='Grid Filters',
                                      disabled=False,
                                    ),
                                  UpwardDistance=widgets.FloatSlider(
                                    min=0, max=500, step=10, value=0,
                                    continuous_update=False
                                    ),
                                  SaveGrid=widgets.ToggleButton(
                                      value=False,
                                      description='Export Grid',
                                      disabled=False,
                                      button_style='',
                                      tooltip='Description',
                                      icon='check'
                                    )

                                  )
    elif gridFilter == 'RTP':
        out = widgets.interactive(plotWidgetRTP,
                                  SunAzimuth=widgets.FloatSlider(
                                    min=0, max=360, step=5, value=90,
                                    continuous_update=False),
                                  SunAngle=widgets.FloatSlider(
                                    min=0, max=90, step=5, value=15,
                                    continuous_update=False),
                                  ColorTransp=widgets.FloatSlider(
                                    min=0, max=1, step=0.05, value=0.9,
                                    continuous_update=False),
                                  HSTransp=widgets.FloatSlider(
                                    min=0, max=1, step=0.05, value=0.50,
                                    continuous_update=False),
                                  vScale=widgets.FloatSlider(
                                    min=1, max=10, step=1., value=5.0,
                                    continuous_update=False),
                                  ColorMap=widgets.Dropdown(
                                      options=cmaps(),
                                      value='RdBu_r',
                                      description='ColorMap',
                                      disabled=False,
                                    ),
                                  Filters=widgets.Dropdown(
                                      options=[
                                        gridFilter,
                                        'TMI'],
                                      value=gridFilter,
                                      description='Grid Filters',
                                      disabled=False,
                                    ),
                                  inc=widgets.FloatText(
                                        value=73,
                                        description='Inclination:',
                                        disabled=False
                                    ),
                                  dec=widgets.FloatText(
                                        value=17,
                                        description='Declination:',
                                        disabled=False
                                    ),
                                  SaveGrid=widgets.ToggleButton(
                                      value=False,
                                      description='Export Grid',
                                      disabled=False,
                                      button_style='',
                                      tooltip='Description',
                                      icon='check'
                                    )
                                  )
    else:
        out = widgets.interactive(plotWidget,
                                  SunAzimuth=widgets.FloatSlider(
                                    min=0, max=360, step=5, value=90,
                                    continuous_update=False),
                                  SunAngle=widgets.FloatSlider(
                                    min=0, max=90, step=5, value=15,
                                    continuous_update=False),
                                  ColorTransp=widgets.FloatSlider(
                                    min=0, max=1, step=0.05, value=0.9,
                                    continuous_update=False),
                                  HSTransp=widgets.FloatSlider(
                                    min=0, max=1, step=0.05, value=0.50,
                                    continuous_update=False),
                                  vScale=widgets.FloatSlider(
                                    min=1, max=10, step=1., value=5.0,
                                    continuous_update=False),
                                  ColorMap=widgets.Dropdown(
                                      options=cmaps(),
                                      value='RdBu_r',
                                      description='ColorMap',
                                      disabled=False,
                                    ),
                                  Filters=widgets.Dropdown(
                                      options=[
                                        gridFilter,
                                        'TMI'],
                                      value=gridFilter,
                                      description='Grid Filters',
                                      disabled=False,
                                    ),
                                  SaveGrid=widgets.ToggleButton(
                                      value=False,
                                      description='Export Grid',
                                      disabled=False,
                                      button_style='',
                                      tooltip='Description',
                                      icon='check'
                                    )
                                  )

    return out


def worldViewerWidget(worldFile, data, grid, z=0):

    world = shapefile.Reader(worldFile)
    # Extract lines from shape file
    X, Y = [], []
    for shape in world.shapeRecords():

        for ii, part in enumerate(shape.shape.parts):

            if ii != len(shape.shape.parts)-1:
                x = [i[0] for i in shape.shape.points[shape.shape.parts[ii]:shape.shape.parts[ii+1]:50]]
                y = [i[1] for i in shape.shape.points[shape.shape.parts[ii]:shape.shape.parts[ii+1]:50]]

            else:
                x = [i[0] for i in shape.shape.points[shape.shape.parts[ii]::50]]
                y = [i[1] for i in shape.shape.points[shape.shape.parts[ii]::50]]

            if len(x) > 10:
                X.append(np.vstack(x))
                Y.append(np.vstack(y))

    def plotCountry(X, Y, ax=None, fill=True, linewidth=1):

        for x, y in zip(X, Y):
            ax.plot(x, y, 'k', linewidth=linewidth)

        return ax

    def plotLocs(placeID):

        selection = int(np.r_[[ii for ii, s in enumerate(list(data.keys())) if placeID in s]])
        dataVals = list(data.values())[selection]

        Xloc, Yloc = np.meshgrid(grid.hx[::5], grid.hy[::5])
        Zloc = np.ones_like(Xloc)*z

        locs = np.c_[mkvc(Xloc), mkvc(Yloc), mkvc(Zloc)]
        survey = ProblemSetter.setSyntheticProblem(locs, EarthField=dataVals[-3:])

        xyz = survey.srcField.rxList[0].locs
        plt.figure(figsize=(10, 8))
        ax1 = plt.subplot(1, 2, 1)
        fig, im, cbar = plotData2D(
          xyz[:, 0], xyz[:, 1], survey.dobs,
          ax=ax1, cmap='RdBu_r', marker=False, colorbar=False
        )

        ax1.set_xticks([0])
        ax1.set_xticklabels([MathUtils.decimalDegrees2DMS(dataVals[1], "Longitude")])
        ax1.set_xlabel('Longitude')
        ax1.set_yticks([0])
        ax1.set_yticklabels([MathUtils.decimalDegrees2DMS(dataVals[0], "Latitude")])
        ax1.set_ylabel('Latitude')
        ax1.grid(True)
        cbar = plt.colorbar(im, orientation='horizontal')
        cbar.set_label('TMI (nT)')

        axs = plt.subplot(1, 2, 2)
        axs = plotCountry(X, Y, ax=axs, fill=False)
        axs.scatter(dataVals[1], dataVals[0], s=50, c='r', marker='s', )
        # axs.set_axis_off()
        axs.set_aspect('equal')
        pos = axs.get_position()
        axs.set_position([pos.x0, pos.y0,  pos.width*1.5, pos.height*1.5])
        axs.patch.set_alpha(0.0)
        # xydata = np.loadtxt("./assets/country-capitals.csv", delimiter=",")
        for key, entry in zip(list(data.keys()), list(data.values())):
            axs.scatter(entry[1], entry[0], c='k')

        axs.set_title(
          "Earth's Field: " + str(int(dataVals[-3])) + "nT, "
          "Inc: " + str(int(dataVals[-2])) + "$^\circ$, "
          "Dec: " + str(int(dataVals[-1])) + "$^\circ$"
        )

        # Add axes with rotating arrow
        pos = axs.get_position()
        arrowAxs = fig.add_axes([10, 10,  pos.width*.5, pos.height*0.5], projection='3d')
        block_xyz = np.asarray([
                        [-.2, -.2, .2, .2, 0],
                        [-.25, -.25, -.25, -.25, 0.5],
                        [-.2, .2, .2, -.2, 0]
                    ])

        # rot = Utils.mkvc(Utils.dipazm_2_xyz(pinc, pdec))

        # xyz = Utils.rotatePointsFromNormals(block_xyz.T, np.r_[0., 1., 0.], rot,
        #                                     np.r_[p.xc, p.yc, p.zc])

        R = MathUtils.rotationMatrix(dataVals[-2], dataVals[-1])

        xyz = R.dot(block_xyz).T

        #print xyz
        # Face 1
        arrowAxs.add_collection3d(Poly3DCollection([list(zip(xyz[[1, 2, 4], 0],
                                                   xyz[[1, 2, 4], 1],
                                                   xyz[[1, 2, 4], 2]))], facecolors='w'))

        arrowAxs.add_collection3d(Poly3DCollection([list(zip(xyz[[0, 1, 4], 0],
                                                   xyz[[0, 1, 4], 1],
                                                   xyz[[0, 1, 4], 2]))], facecolors='k'))

        arrowAxs.add_collection3d(Poly3DCollection([list(zip(xyz[[2, 3, 4], 0],
                                                   xyz[[2, 3, 4], 1],
                                                   xyz[[2, 3, 4], 2]))], facecolors='w'))

        arrowAxs.add_collection3d(Poly3DCollection([list(zip(xyz[[0, 3, 4], 0],
                                               xyz[[0, 3, 4], 1],
                                               xyz[[0, 3, 4], 2]))], facecolors='k'))

        arrowAxs.add_collection3d(Poly3DCollection([list(zip(xyz[:4, 0],
                                                   xyz[:4, 1],
                                                   xyz[:4, 2]))], facecolors='r'))

        arrowAxs.view_init(30, -90)
        arrowAxs.set_xlim([-0.5, 0.5])
        arrowAxs.set_ylim([-0.5, 0.5])
        arrowAxs.set_zlim([-0.5, 0.5])
        arrowAxs.set_xticks([])
        arrowAxs.set_yticks([])
        arrowAxs.set_zticks([])
        # arrowAxs.set_aspect('equal')

        plt.show()

        return axs

    out = widgets.interactive(plotLocs,
                        placeID = widgets.Dropdown(
                        options=list(data.keys()),
                        value=list(data.keys())[0],
                        description='Location:',
                        disabled=False,
                        ))

    return out


def dataGriddingWidget(survey, EPSGCode=26909, fileName='DataGrid'):

    def plotWidget(
            Resolution, Method,
            Contours, ColorMap,
            SaveGrid
         ):

        if Method == 'minimumCurvature':
            gridCC, d_grid = MathUtils.minCurvatureInterp(
                np.c_[xLoc, yLoc], survey.dobs,
                gridSize=Resolution, method='spline'
                )
            X = gridCC[:, 0].reshape(d_grid.shape, order='F')
            Y = gridCC[:, 1].reshape(d_grid.shape, order='F')

        else:
            npts_x = int((xLoc.max() - xLoc.min())/Resolution)
            npts_y = int((yLoc.max() - yLoc.min())/Resolution)

            # Create grid of points
            vectorX = np.linspace(xLoc.min(), xLoc.max(), npts_x)
            vectorY = np.linspace(yLoc.min(), yLoc.max(), npts_y)

            X, Y = np.meshgrid(vectorX, vectorY)

            d_grid = griddata(np.c_[xLoc, yLoc], data, (X, Y), method=Method)

        if SaveGrid:
            DataIO.arrayToRaster(
                d_grid, fileName + '.tiff',
                EPSGCode, X.min(), X.max(),  Y.min(), Y.max(), 1,
                dataType='grid')

        else:
            fig = plt.figure(figsize=(9, 9))
            axs = plt.subplot()
            # Add shading
            X, Y, d_grid, im, CS = plotDataHillside(
                X, Y, d_grid, alpha=1., contours=Contours,
                axs=axs, cmap=ColorMap, clabel=False)

            # Add points at the survey locations
            plt.scatter(xLoc, yLoc, s=2, c='k')
            axs.set_aspect('auto')
            cbar = plt.colorbar(im, fraction=0.02)
            cbar.set_label('TMI (nT)')

            axs.set_xlabel("Easting (m)", size=14)
            axs.set_ylabel("Northing (m)", size=14)
            axs.grid('on', color='k', linestyle='--')
            plt.show()

        # Create grid object
        gridOut = DataIO.dataGrid()

        gridOut.values = d_grid
        gridOut.nx, gridOut.ny = gridOut.values.shape[1], gridOut.values.shape[0]
        gridOut.x0, gridOut.y0 = X.min(), Y.min()
        gridOut.dx = (X.max() - X.min()) / gridOut.values.shape[1]
        gridOut.dy = (Y.max() - Y.min()) / gridOut.values.shape[0]
        gridOut.limits = np.r_[gridOut.x0, gridOut.x0+gridOut.nx*gridOut.dx, gridOut.y0, gridOut.y0+gridOut.ny*gridOut.dy]
        return gridOut

    # Calculate the original map extents
    xLoc = survey.srcField.rxList[0].locs[:, 0]
    yLoc = survey.srcField.rxList[0].locs[:, 1]
    data = survey.dobs

    out = widgets.interactive(plotWidget,
                              Resolution=widgets.FloatText(
                                        value=10,
                                        description='Grid (m):',
                                        disabled=False
                                ),
                              Method=widgets.Dropdown(
                                  options=[
                                    'nearest', 'linear', 'cubic',
                                    'minimumCurvature'
                                    ],
                                  value='minimumCurvature',
                                  description='Method',
                                  disabled=False,
                                ),
                              Contours=widgets.IntSlider(
                                    min=10, max=100, step=10,
                                    value=50, continuous_update=False
                                ),
                              ColorMap=widgets.Dropdown(
                                  options=cmaps(),
                                  value='RdBu_r',
                                  description='ColorMap',
                                  disabled=False,
                                ),
                              SaveGrid=widgets.ToggleButton(
                                  value=False,
                                  description='Export Grid',
                                  disabled=False,
                                  button_style='',
                                  tooltip='Description',
                                  icon='check'
                                )
                              )
    return out