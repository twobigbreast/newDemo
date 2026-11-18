"""Deterministic educational models, no observational data are fabricated."""
import math
G=4.30091e-6  # kpc (km/s)^2 / solar mass
BARYON_MASS=5.5e10
BARYON_SCALE=2.8  # kpc, extended Plummer sphere, NOT a disk point mass
HALO_CORE=3.0  # kpc, pseudo-isothermal sphere
HALO_ASYMPTOTIC_SPEED=200.0  # km/s

def baryon_mass(r):return BARYON_MASS*r**3/(r*r+BARYON_SCALE**2)**1.5

def baryon_speed(r):return math.sqrt(G*baryon_mass(r)/r) if r>0 else 0.

def halo_speed(r):
 x=r/HALO_CORE
 return HALO_ASYMPTOTIC_SPEED*math.sqrt(max(0,1-math.atan(x)/x)) if x>0 else 0.

def total_speed(r):return math.hypot(baryon_speed(r),halo_speed(r))

def illustrative_observation_trend(r):return 210*(1-math.exp(-r/2.0))

def cluster_positions(q):
 # Galaxies and mostly collisionless mass move through; gas is slowed near center.
 q=max(0.,min(1.,q));travel=-270+570*q
 gas=-270+225*q if q<.5 else -157.5+100*(q-.5)
 return (960+travel,960-travel),(960+gas,960-gas)
