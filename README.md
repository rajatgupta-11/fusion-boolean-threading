# Fusion 360 Boolean Threading Script

This script automates a specific workflow for creating reliable 3D-printed threads in Fusion 360. Makes thread modeling automated, safe, repeatable. 

## What the script does

The script performs the following operations, in order:

- Creates a modeled external thread on a selected cylindrical face (parent body)
- Creates a lead-in chamfer and reorders it in the timeline so Fusion recalculates the thread entry correctly
- Subtracts the threaded geometry from the mating body so both parts share identical thread geometry
- Applies a user-defined clearance offset to the internal thread

The result is a thread pair that prints cleanly, engages smoothly, and behaves predictably without supports.


## Orientation and lead-in edge detection

The script determines the lead-in edge using the cylinder’s own axis, not world coordinates.

The top edge is defined as:

> the circular edge furthest from the cylinder’s origin along the cylinder’s axis vector

This means:

- the part can be oriented arbitrarily
- the bolt does not need to point upward
- world Z is irrelevant

As long as the selected face is a true cylinder, the correct lead-in edge is identified.


## Required setup before running

Before running the script:

- Parent and mating bodies must already be positioned correctly
- Bodies must overlap in the expected assembled configuration
- The selected face on the parent must be a clean cylindrical face

The script does not align or move bodies.


## How to use

### Install

1. Open Fusion 360  
2. Go to **Utilities → Scripts and Add-Ins**  
3. Open the **Scripts** tab  
4. Click **Create**  
5. Choose **Python**  
6. Name the script (for example: `BooleanThreading`)  
7. Paste the `.py` file contents  
8. Save  


### Run

When executed, the script will prompt you to:

- Select the parent body (bolt or stud)
- Select the mating body (lid or nut)
- Select the cylindrical face on the parent to thread
- Choose the thread designation manually  
  - The script estimates diameter  
  - You must explicitly choose the designation  
  - This is intentional
- Select the internal thread face on the mating body
- Enter a clearance offset

## Clearance tuning

Clearance controls speed vs fit.

Typical starting values:

- **0.2 mm** → Bambu X1E, PLA, fast iteration  
- **0.1 mm** → resin or higher-precision prints  

Smaller clearance:

- tighter fit
- higher friction
- slower engagement

Larger clearance:

- faster engagement
- looser fit
- better for repeated assembly

There is no universal correct value. Tune based on printer, material, and use case.

If the fit tightens instead of loosens, flip the sign of the offset.

## Assumptions and limitations

- Requires a clean cylindrical face
- Requires ISO Metric thread library in Fusion
- Offset direction depends on face normal orientation
- Thread size selection is intentionally manual

This script encodes a workflow, not a one-click solution.

## Intended use

This is for:

- functional printed threads
- iterative mechanical parts
- cases where thread behavior matters more than nominal dimensions


## Why boolean threading

Creating matching thread features on two separate parts fails in practice because:

- helix geometry is generated independently per feature
- slicers discretize that geometry independently
- small geometric differences stack immediately in printed threads

By modeling the thread once and subtracting it from the mating part, both parts inherit the exact same geometry. Clearance is then applied explicitly instead of implicitly.

This removes a large class of failure modes.


## Why feature order matters

Fusion allows chamfering before or after threading, but the order affects the resulting geometry.

If the chamfer is applied incorrectly, Fusion often produces:

- a sharp step at the start of the helix
- a non-clean lead-in edge
- poor first-turn engagement in printed parts

This script enforces the following sequence:

1. Create the modeled thread  
2. Create the chamfer  
3. Move the chamfer ahead of the thread in the timeline  

Reordering forces Fusion to recompute the thread entry using the chamfered base geometry. This eliminates the stepped helix start that shows up immediately in prints.

---
