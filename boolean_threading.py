import adsk.core, adsk.fusion, traceback, re

def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui  = app.userInterface
        design = adsk.fusion.Design.cast(app.activeProduct)
        root = design.rootComponent
        unitsMgr = design.unitsManager

        # --- 1. SELECTION & VALIDATION ---
        ui.messageBox('Select Parent (Bolt), then Mating Part (Lid), then the Face to Thread.')
        
        pSel = ui.selectEntity('Select Parent Body (Bolt)', 'Bodies')
        parentBody = adsk.fusion.BRepBody.cast(pSel.entity)

        cSel = ui.selectEntity('Select Mating Body (Lid)', 'Bodies')
        childBody = adsk.fusion.BRepBody.cast(cSel.entity)

        fSel = ui.selectEntity('Select Cylindrical Face on Parent', 'Faces')
        threadFace = adsk.fusion.BRepFace.cast(fSel.entity)

        # Body ownership check
        if threadFace.body != parentBody:
            ui.messageBox('Error: Face must belong to the Parent Body.')
            return

        # CYLINDRICAL VALIDATION (Re-added for robustness)
        if threadFace.geometry.surfaceType != adsk.core.SurfaceTypes.CylinderSurfaceType:
            ui.messageBox('Error: Selected face must be cylindrical. Threads cannot be applied to this geometry.')
            return

        # --- 2. AXIS-BASED TOP EDGE DETECTION ---
        cyl = threadFace.geometry
        axis = cyl.axis
        origin = cyl.origin
        
        topEdge = None
        maxDist = -float('inf')
        
        for edge in threadFace.edges:
            if edge.geometry.curveType == adsk.core.CurveTypes.Circle3dCurveType:
                center = edge.geometry.center
                dist = origin.vectorTo(center).dotProduct(axis)
                if dist > maxDist:
                    maxDist = dist
                    topEdge = edge

        if not topEdge:
            ui.messageBox('Error: Could not identify a circular lead-in edge on the cylinder.')
            return

        # --- 3. THREADING (CREATE FIRST) ---
        diameter_mm = unitsMgr.convert(cyl.radius * 2, unitsMgr.internalUnits, 'mm')
        threadFeats = root.features.threadFeatures
        query = threadFeats.threadDataQuery
        
        targetType = next((t for t in query.allThreadTypes if 'ISO Metric' in t), None)
        if not targetType:
            ui.messageBox('ISO Metric profile not found in your Fusion library.')
            return

        allSizes = query.allSizes(targetType)
        def get_num(s):
            m = re.search(r"(\d+)", s)
            return float(m.group(1)) if m else 0.0
        
        bestSize = min(allSizes, key=lambda x: abs(get_num(x) - diameter_mm))
        
        designations = query.allDesignations(targetType, bestSize)
        msg = f"Detected ~{round(diameter_mm, 2)}mm diameter. Select Designation:\n"
        for i, d in enumerate(designations):
            msg += f"[{i}]: {d}\n"
        
        idxInput, isCancelled = ui.inputBox(msg, "Thread Selection", "0")
        if isCancelled: return
        
        try:
            threadDesignation = designations[int(idxInput)]
        except:
            ui.messageBox('Invalid index selected.')
            return
        
        threadInfo = threadFeats.createThreadInfo(False, targetType, bestSize, threadDesignation, '6g')
        tInput = threadFeats.createInput(threadFace, threadInfo)
        tInput.isModeled = True
        tInput.isFullLength = True
        threadFeature = threadFeats.add(tInput)

        # --- 4. CHAMFER (CREATE SECOND) ---
        chamferFeats = root.features.chamferFeatures
        edgeCol = adsk.core.ObjectCollection.create()
        edgeCol.add(topEdge)
        chamferInput = chamferFeats.createInput(edgeCol, True)
        chamferInput.addDistanceChamferEdgeSet(edgeCol, adsk.core.ValueInput.createByString('1.0 mm'), True)
        chamferFeature = chamferFeats.add(chamferInput)

        # --- 5. TIMELINE SURGERY (REORDER) ---
        try:
            timeline = design.timeline
            chamferItem = timeline.item(chamferFeature.timelineObject.index)
            threadItem = timeline.item(threadFeature.timelineObject.index)
            chamferItem.moveToPosition(threadItem.index)
        except:
            ui.messageBox('Warning: Timeline reorder failed. Please manually drag the Chamfer before the Thread.')

        # --- 6. BOOLEAN SUBTRACTION ---
        toolCols = adsk.core.ObjectCollection.create()
        toolCols.add(parentBody)
        combInput = root.features.combineFeatures.createInput(childBody, toolCols)
        combInput.operation = adsk.fusion.FeatureOperations.CutOperation
        combInput.isKeepToolBodies = True
        root.features.combineFeatures.add(combInput)

        # --- 7. CLEARANCE (USER INPUT) ---
        ui.messageBox('Select the resulting internal thread face on the Mating Body.')
        targetFace = ui.selectEntity('Select internal thread face', 'Faces').entity
        
        offsetStr, isCancelled = ui.inputBox("Enter clearance (mm)\n(Try 0.2 for Bambu X1E, 0.1 for Resin)", "Clearance", "0.2")
        if isCancelled: return
        
        faceCol = adsk.core.ObjectCollection.create()
        faceCol.add(targetFace)
        # Offset direction note: - normally creates clearance in this context
        offsetVal = adsk.core.ValueInput.createByString(f"-{offsetStr} mm")
        offsetInput = root.features.offsetFeatures.createInput(faceCol, offsetVal, adsk.fusion.FeatureOperations.ModifyFeatureOperation, False)
        root.features.offsetFeatures.add(offsetInput)

        ui.messageBox('Workflow complete. Inspect the lead-in and test the fit.')

    except:
        if ui:
            ui.messageBox('Fatal Error:\n{}'.format(traceback.format_exc()))
