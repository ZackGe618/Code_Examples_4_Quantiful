# -*- coding: utf-8 -*-
#--------------------------------------------------------------------------------#
# This is a python FWI calculator based on Wang 2015 and Lawson et al., 2008.
# Modified by @Jiawei Zhang (jiawei.zhang@canterbury.ac.nz), 2022
# The code is adpated from Wang et al, 2015 (Updated source code for calculating fire danger indices
# in the Canadian Forest Fire Weather Index System.) 
# To be able to apply on xarray dataarray objects and also speed up the calculation, 
# the code has also been vectorized and paralleled utilizing dask and numba libraries by @Jiawei Zhang.
# The daytime length factors for DMC and DC are adjusted based on NZ latitude range and Lawson et al., 2008.
# Input temperature should be degree celsius,rain should be in mm,relative humidity should be between 0 and 100.
#--------------------------------------------------------------------------------#

import datetime
import numpy as np
import xarray as xr
from numba import float32, float64, guvectorize, int64, vectorize
import warnings
warnings.filterwarnings('ignore')

@vectorize([float64(float64, float64,float64,float64,float64)])
def FFMCcalc(temperature,rel_hum,wind_speed,precipitation,ffmc0):

    mo = (147.2*(101.0 - ffmc0))/(59.5 + ffmc0)                                               #*Eq. 1*#
    if (precipitation > 0.5): 
        rf = precipitation - 0.5                                                                     #*Eq. 2*#
        if(mo > 150.0):
            mo = (mo+42.5*rf*np.exp(-100.0/(251.0-mo))* (1.0 - np.exp(-6.93/rf))) \
            + (.0015*(mo - 150.0)**2)*np.sqrt(rf)                                           #*Eq. 3b*#
        elif mo <= 150.0:
            mo = mo+42.5*rf*np.exp(-100.0/(251.0-mo))*(1.0 - np.exp(-6.93/rf))            #*Eq. 3a*#
        if(mo > 250.0):
            mo = 250.0
    elif np.isnan(precipitation):                                                           # add this elif to make sure that ffmc is nan when precipitation is nan
        mo = np.nan

    ed = 0.942*(rel_hum**.679) + (11.0*np.exp((rel_hum-100.0)/10.0))+0.18*(21.1-temperature)\
    *(1.0 - 1.0/np.exp(.1150 * rel_hum))                                                     #*Eq. 4*#

    if(mo < ed):
        ew = .618*(rel_hum**.753) + (10.0*np.exp((rel_hum-100.0)/10.0)) \
        + .18*(21.1-temperature)*(1.0 - 1.0/np.exp(.115 * rel_hum))                              #*Eq. 5*#
        if(mo <= ew):
            kl = .424*(1.0-((100.0-rel_hum)/100.0)**1.7)+(.0694*np.sqrt(wind_speed)) \
            *(1.0 - ((100.0 - rel_hum)/100.0)**8)                                                  #*Eq. 7a*#
            kw = kl * (.581 * np.exp(.0365 * temperature))                                           #*Eq. 7b*#
            m = ew - (ew - mo)/10.0**kw                                                           #*Eq. 9*#
        elif mo > ew:
            m = mo
    elif(mo == ed):
        m = mo
    elif mo > ed:
        kl =.424*(1.0-(rel_hum/100.0)**1.7)+(.0694*np.sqrt(wind_speed))* \
        (1.0-(rel_hum/100.0)**8)                                                                   #*Eq. 6a*#
        kw = kl * (.581*np.exp(.0365*temperature))                                                 #*Eq. 6b*# 
        m = ed + (mo-ed)/10.0 ** kw                                                           #*Eq. 8*#
    elif np.isnan(mo):                                                                   # add this elif to make sure that ffmc is nan when precipitation is nan
        m = np.nan

    ffmc = (59.5 * (250.0 -m)) / (147.2 + m)                                                 #*Eq. 10*#
    if (ffmc > 101.0):
        ffmc = 101.0
    elif (ffmc<= 0.0):
        ffmc = 0.0
    return ffmc

@vectorize([float64(float64, float64,float64,float64,int64)])
def DMCcalc(temperature,rel_hum,precipitation,dmc0,mth):
    
    el = [11.5, 10.5,  9.2,  7.9,  6.8,  6.2,  6.5,  7.4,  8.7, 10.0, 11.2, 11.8]         #NZ adjusted

    t = temperature

    if (t < -1.1):
        t = -1.1
    rk = 1.894*(t+1.1) * (100.0-rel_hum) * (el[mth-1]*0.0001)                                   #*Eqs. 16 and 17*#

    if precipitation > 1.5:
        ra= precipitation
        rw = 0.92*ra - 1.27                                                                        #*Eq. 11*# 
        wmi = 20.0 + 280.0/np.exp(0.023*dmc0)                                                   #*Eq. 12*#

        if dmc0 <= 33.0:
            b = 100.0 /(0.5 + 0.3*dmc0)                                                          #*Eq. 13a*#
        elif dmc0 > 33.0:
            if dmc0 <= 65.0:
                b = 14.0 - 1.3*np.log(dmc0)                                                   #*Eq. 13b*#
            elif dmc0 > 65.0:
                b = 6.2 * np.log(dmc0) - 17.2                                                  #*Eq. 13c*#

        wmr = wmi + (1000*rw) / (48.77+b*rw)                                                     #*Eq. 14*#
        pr = 43.43 * (5.6348 - np.log(wmr-20.0))                                               #*Eq. 15*#

    elif precipitation <= 1.5:
        pr = dmc0
        
    else:
        pr = np.nan

    if (pr<0.0):
        pr = 0.0
    dmc = pr + rk

    if(dmc<= 1.0):
        dmc = 1.0
    return dmc

@vectorize([float64(float64,float64,float64,int64)])
def DCcalc(temperature,precipitation,dc0,mth):
    
    fl = [6.4, 5.0, 2.4, 0.4, -1.6, -1.6, -1.6, -1.6, -1.6, 0.9, 3.8, 5.8]          #NZ adjusted
    t = temperature
    if(t < -2.8):
        t = -2.8

    pe = (0.36*(t+2.8) + fl[mth-1] )/2                                                       #*Eq. 22*#
    if pe <= 0.0:
        pe = 0.0

    if (precipitation > 2.8):
        ra = precipitation
        rw = 0.83*ra - 1.27                                                                   #*Eq. 18*#
        smi = 800.0 * np.exp(-dc0/400.0)                                                     #*Eq. 19*# 
        dr = dc0 - 400.0*np.log( 1.0+((3.937*rw)/smi) )                                   #*Eqs. 20 and 21*#
        if (dr > 0.0):
            dc = dr + pe
    elif precipitation <= 2.8:
        dc = dc0 + pe
    else:
        dc = np.nan
    return dc

@vectorize([float64(float64,float64)])
def ISIcalc(wind_speed,ffmc):

    mo = 147.2*(101.0-ffmc) / (59.5+ffmc)                                                  #*Eq. 1*#

    ff = 19.115*np.exp(mo*-0.1386) * (1.0+(mo**5.31)/49300000.0)                         #*Eq. 25*#

    isi = ff * np.exp(0.05039*wind_speed)                                                    #*Eq. 26*#

    return isi

@vectorize([float64(float64,float64)])
def BUIcalc(dmc,dc):

    if dmc <= 0.4*dc:

        bui = (0.8*dc*dmc) / (dmc+0.4*dc)                                             #*Eq. 27a*#
    else:
        bui = dmc-(1.0-0.8*dc/(dmc+0.4*dc))*(0.92+(0.0114*dmc)**1.7)                  #*Eq. 27b*#

    if bui <0.0:
        bui = 0.0
    return bui

@vectorize([float64(float64,float64)])
def FWIcalc(isi,bui):

    if bui <= 80.0:
        bb = 0.1 * isi * (0.626*bui**0.809 + 2.0)                                     #*Eq. 28a*#
    else:
        bb = 0.1*isi*(1000.0/(25. + 108.64/np.exp(0.023*bui)))                      #*Eq. 28b*#

    if(bb <= 1.0):
        fwi = bb                                                                      #*Eq. 30b*#
    else:
        fwi = np.exp(2.72 * (0.434*np.log(bb))**0.647)                            #*Eq. 30a*#

    return fwi

def FWI_input_prep(temperature,rel_hum,wind_speed,precipitation,start_date=None,end_date=None,input_time_zone = "UTC"):
    ###
    #get the daily data which inclues noon temperature,rh,wind_speed and also 24 hour rainfail from previous noon to current noon
    #if there is no noon time index in the data, it will skip that day.
    #todo: time zone not implimented yet...
    ###

    #get start and end date
    if start_date == None:
        start_date = precipitation.time[0] + np.timedelta64(1,'D')
    elif ((np.datetime64(start_date) -  np.timedelta64(1,'D') ) < precipitation.time[0]):
        start_date = precipitation.time[0] + np.timedelta64(1,'D')
    if end_date == None:
        end_date = precipitation.time[-1]
    elif np.datetime64(end_date) > precipitation.time[-1]:
        end_date = precipitation.time[-1]
    
    precipitation_noon = precipitation.resample(time="24H",base=0,loffset="24H").sum().sel(time=slice(start_date, end_date)) # assume precipitation is hourly accumulated.
    
    rel_hum_noon = rel_hum.resample(time="1D").nearest(tolerance="0h").sel(time=slice(start_date, end_date))
    rel_hum_noon = rel_hum_noon.where(rel_hum_noon<=100.0, 100.0) ### maximum relative humidity set to 100.0.
    temperature_noon = temperature.resample(time="1D").nearest(tolerance="0h").sel(time=slice(start_date, end_date))
    wind_speed_noon = wind_speed.resample(time="1D").nearest(tolerance="0h").sel(time=slice(start_date, end_date))
    
    ### change all the variables to nan if there is only one variable is nan
    val_mask = (precipitation_noon.notnull() & rel_hum_noon.notnull() & temperature_noon.notnull()& wind_speed_noon.notnull())
    precipitation_noon = precipitation_noon.where(val_mask,np.nan)
    rel_hum_noon = rel_hum_noon.where(val_mask,np.nan)
    temperature_noon = temperature_noon.where(val_mask,np.nan)
    wind_speed_noon = wind_speed_noon.where(val_mask,np.nan)
    
    return temperature_noon, rel_hum_noon, wind_speed_noon, precipitation_noon

def FWI_step_calc(temperature,rel_hum,wind_speed,precipitation,mth,ffmc0,dmc0,dc0):
    ### step function to calculate FWI
    # assume that each of the input is a single timestep matrix with multiple spatial data points
    ###
    
    ffmc = xr.apply_ufunc(
        FFMCcalc,  # first the function
        temperature,
        rel_hum,
        wind_speed,
        precipitation,
        ffmc0,
        dask="parallelized",
        output_dtypes=np.float64,  # one per output
    )



    dmc = xr.apply_ufunc(
        DMCcalc,  # first the function
        temperature,
        rel_hum,
        precipitation,
        dmc0,
        mth,
        dask="parallelized",
        output_dtypes=np.float64,  # one per output
    )
    
    dc = xr.apply_ufunc(
        DCcalc,  # first the function
        temperature,
        precipitation,
        dc0,
        mth,
        dask="parallelized",
        output_dtypes=np.float64,  # one per output
    )

    isi= xr.apply_ufunc(
        ISIcalc,  # first the function
        wind_speed,
        ffmc,
        dask="parallelized",
        output_dtypes=np.float64,  # one per output
    )
    

    bui = xr.apply_ufunc(
        BUIcalc,  # first the function
        dmc,
        dc,
        dask="parallelized",
        output_dtypes=np.float64,  # one per output
    )


    fwi = xr.apply_ufunc(
        FWIcalc,  # first the function
        isi,
        bui,
        dask="parallelized",
        output_dtypes=np.float64,  # one per output
    )
    
    return ffmc, dmc, dc, isi, bui, fwi


def FWI_combined_calc(temperature,rel_hum,wind_speed,precipitation,ffmc0=85.0,dmc0=6.0,dc0=15.0,start_date=None,end_date=None,ws_unit=None):
    ### main function to calculate FWI
    assert ws_unit == 'm/s' or ws_unit == 'km/h',\
    "No valid windspeed unit provided, Please specify the unit of wind speed. Accepted values are 'm/s','km/h'"
    if  ws_unit == "m/s":
        wind_speed = wind_speed*3.6
              
    # prepare FWI input data
    temperature_noon,rel_hum_noon,wind_speed_noon, precipitation_noon = FWI_input_prep(temperature,rel_hum,wind_speed,precipitation,start_date,end_date)
    
    # get month index
    mth = precipitation_noon.time.dt.month
    
    # initialized the FWI dataarray
    fwi_da = precipitation_noon.copy(deep=True)
    fwi_da.name = "FWI"
    fwi_da.attrs = dict()
    
    ffmc0_da  = wind_speed_noon.isel(time=0)
    dmc0_da = ffmc0_da.copy(deep=True)
    dc0_da     = ffmc0_da.copy(deep=True)
    
    ffmc0_da = ffmc0_da.where(ffmc0_da.isnull(),ffmc0)
    dmc0_da = dmc0_da.where(dmc0_da.isnull(),dmc0)
    dc0_da = dc0_da.where(dc0_da.isnull(),dc0)

    #three varaibles to record all the intermidiate ffmc,dmc and dc values, can be removed if needed.
    ffmc_da = fwi_da.copy(deep=True)
    ffmc_da.name = "FFMC"
    ffmc_da.attrs = dict()
    dmc_da = fwi_da.copy(deep=True)
    dmc_da.name = "DMC"
    dmc_da.attrs = dict()
    dc_da = fwi_da.copy(deep=True)
    dc_da.name = "DC"
    dc_da.attrs = dict()
    isi_da = fwi_da.copy(deep=True)
    isi_da.name = "ISI"
    isi_da.attrs = dict()
    bui_da = fwi_da.copy(deep=True)
    bui_da.name = "BUI"
    bui_da.attrs = dict()    
    
    #start time step
    for i in range(0,fwi_da.time.shape[0]):
        #print(i)
        ffmc_tmp,dmc_tmp,dc_tmp,isi_tmp,bui_tmp,fwi_tmp = FWI_step_calc(temperature_noon.isel(time=i),rel_hum_noon.isel(time=i),\
                                                      wind_speed_noon.isel(time=i),precipitation_noon.isel(time=i),\
                                                      mth.isel(time=i),ffmc0_da,dmc0_da,dc0_da)
        
        ffmc_da.loc[dict(time=fwi_da.time[i])] = ffmc_tmp
        dmc_da.loc[dict(time=fwi_da.time[i])] = dmc_tmp
        dc_da.loc[dict(time=fwi_da.time[i])] = dc_tmp
        isi_da.loc[dict(time=fwi_da.time[i])] = isi_tmp
        bui_da.loc[dict(time=fwi_da.time[i])] = bui_tmp
        fwi_da.loc[dict(time=fwi_da.time[i])] = fwi_tmp
        
        ### if somehoe the current one is nan, then use the previous value to caculate the next time step.
        ffmc0_da = ffmc_tmp.where(ffmc_tmp.notnull(),ffmc0_da).compute()
        dmc0_da = dmc_tmp.where(dmc_tmp.notnull(),dmc0_da).compute()
        dc0_da = dc_tmp.where(dc_tmp.notnull(),dc0_da).compute()
        
    return ffmc_da,dmc_da,dc_da,isi_da,bui_da,fwi_da


def wind_speed_from_component(u,v):
    # This has nothing to do with fwi calculation.
    # Just in case for simulation data, one doesn't have wind speed but u and v components.
    # This can be used to calculate wind speed.
    wspeed = xr.ufuncs.sqrt(u * u + v * v )
    wspeed.attrs["long_name"] = r"$Wind\ speed$"
    wspeed.attrs["units"] = r"$m\ s^{-1}$"
    wspeed.name = "wind speed"
    return wspeed