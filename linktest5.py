bl_info = {
    "name": "objectflowerprocess2",
    "blender": (2, 80, 0),
    "category": "Object",
}

import bpy
import bmesh
import math
from mathutils import *


class ObjectFlowerProcess2(bpy.types.Operator):
    """Object Flower Process2"""
    bl_idname = "object.flower_process2"
    bl_label = "Flower Process2"
    bl_options = {'REGISTER', 'UNDO'}
    
    """
    Guidelines for petal design:
        - Petals MUST be represented as beveled splines. Do not triangulate/represent as a mesh
        - Script only works with petals composed of a contiguous spline with 3 control points
        - Script does not handle intersections, so getting a good configuration may require some testing --> Set thickness of spline beforehand!
        - Center must not be the same as one of Nurb/Spline endpoints --> Place center at origin, between the two ends of the petal
        - First Nurb/Spline endpoint must be the one connected to center of link
        - Petals should face toward the x-axis!
    Guidelines for planar sheet:
        - Sheet must be a plane orthogonal to the z-axis --> Preferably set at z=0
        - May need to cull sheet for triangles that are too small (Automatically pre-process? Perhaps by length of edges?)
    """
    def execute(self, context):
        ctx = context.copy()
        scene = context.scene
        cursor = scene.cursor.location
        obj = context.active_object
        obj2 = bpy.data.objects['Petal']
        obj3 = bpy.data.objects['PetalOpen']    # Open links
         # Load in and store object data
        me = context.active_object.data
        me2 = obj2.data
        me3 = obj3.data
        bm = bmesh.new()   # create an empty BMesh object
        bm.from_mesh(me)   # fill it in from a Mesh

        # Calculate petal overhang
        petal_max_x = -float('inf')
        for v in obj2.bound_box:
            if (v[0] > petal_max_x):
                petal_max_x = v[0]
        
        # Create a new collection to store our copied spline objects
        petal_collection = bpy.data.collections.new("PetalCollection")
        bpy.context.scene.collection.children.link(petal_collection)
        
        mesh_petal_collection = bpy.data.collections.new("MeshPetalCollection")
        bpy.context.scene.collection.children.link(mesh_petal_collection)
        
        # Main Operation Loop: Loops over all edge. For each edge in that face, add two petal oriented in opposite directions.
        for edge in bm.edges:   # Iterate over mesh edge
            edge_length = (edge.verts[1].co - edge.verts[0].co).magnitude
            if (edge_length/2 > petal_max_x + 0.5):
                #open_petal = False # Set to true if we select the open petal type
                midedge = mid_edge(edge)    # Find edge midpoint
                rot = edge_rot(edge)    # Find rotation angle from edge.co[0] to edge.co[1]
                rot2 = rot + math.pi
                    
                # Test if boundary and deep copy the corresponding link
                # CHANGE TO (> 1) instead of (>= 1) if you want to test edge links.
                #if (len(edge.link_faces) > 1):
                new_petal = obj2.copy()
                new_petal.data = obj2.data.copy()
                new_petal2 = obj2.copy()
                new_petal2.data = obj2.data.copy()
                """else:   # If edge is only adjacent to one face then it must be a boundary
                    new_petal = obj3.copy()
                    new_petal.data = obj3.data.copy()
                    open_petal = True"""
                # Add new petal to our scene
                petal_collection.objects.link(new_petal)
                petal_collection.objects.link(new_petal2)
                
                # Petal 1
                end_trans = Vector((-(midedge - (edge.verts[0].co)).magnitude, 0, 0))
                control_point = new_petal.data.splines[0].bezier_points[0]
                control_point.co = end_trans
                
                control_point2 = new_petal.data.splines[0].bezier_points[2]
                control_point2.co = end_trans    
                
                # Translate petal to middle of edge
                new_petal.location = midedge
                # Rotate 
                new_petal.rotation_euler[2] = rot
                
                apply_petal_transforms(new_petal)
                
                # Copy the petal into a mesh
                mesh = bpy.data.meshes.new_from_object(new_petal)
                new_obj = bpy.data.objects.new(new_petal.name, mesh)
                new_obj.matrix_world = obj.matrix_world
                mesh_petal_collection.objects.link(new_obj)
                
                # Petal 2
                control_point = new_petal2.data.splines[0].bezier_points[0]
                control_point.co = end_trans
                
                control_point2 = new_petal2.data.splines[0].bezier_points[2]
                control_point2.co = end_trans    
                
                # Translate petal to middle of edge
                new_petal2.location = midedge
                # Rotate 
                new_petal2.rotation_euler[2] = rot2
                
                apply_petal_transforms(new_petal2)
                
                # Copy the petal into a mesh
                mesh2 = bpy.data.meshes.new_from_object(new_petal2)
                new_obj2 = bpy.data.objects.new(new_petal2.name, mesh2)
                new_obj2.matrix_world = obj.matrix_world
                mesh_petal_collection.objects.link(new_obj2)


        
        # Clear Select
        bpy.ops.object.select_all(action='DESELECT')
        
        # Remove our temporary spline collection
        for pet in petal_collection.objects:
            bpy.data.objects.remove(pet, do_unlink=True)
        bpy.data.collections.remove(petal_collection)
        
        # Finish up, write the bmesh back to the mesh
        bm.to_mesh(me)
        bm.free()  # free and prevent further access of local variable
        
        return {'FINISHED'}

# Returns edge midpoint
def mid_edge(e):       
    return (e.verts[0].co + e.verts[1].co) / 2

# Retrieves one of the edge normals and finds rotation angle (assumes planar + orthogonal to z-axis)
def edge_rot(e):
    v1 = e.verts[0].co
    v2 = e.verts[1].co
    e_vec = v2 - v1
    e_vec.normalize()
    zero_deg = Vector((1.0, 0., 0.))
    cross_p = zero_deg.cross(e_vec)
    rot = math.asin(cross_p.magnitude)
    # Handle horizontal and vertical edge cases
    """if (e_vec[1] == 0):
        if (e_vec[0] > 0):
            rot = math.pi/2
        else:
            rot = 3*math.pi/2
    elif (e_vec[0] == 0):
        if (e_vec[1] > 0):
            rot = math.pi
        else:
            rot = 0"""
    if ((e_vec[1] < 0) and (e_vec[0] > 0)) or ((e_vec[1] > 0) and (e_vec[0] < 0)):
        rot *= -1
    # To get the angle, simply use dot prod with some global axis dir. Also returns the normalized normal
    return rot

# Finds centroid of a triangular face
def find_face_center(f):
    # Centroid!
    num_v = 0
    center = Vector((0., 0., 0.))
    for loop in f.loops:
        vert = loop.vert
        num_v += 1
        center[0] += vert.co[0]
        center[1] += vert.co[1]
        center[2] += vert.co[2]
    center /= num_v
    
    return center

# Tests if the center of the current face is on the same side of an edge as our calculated normal
# Returns true if not; false if in
def test_halfplane(norm, cm):
    cm2 = Vector((cm[0], cm[1], cm[2]))
    return (norm.dot(cm2) >= 0)
    
# Finds the location of the vertex that the current edge comes from (CCW)
def find_from_vertex(norm, edge, fc):
    up = Vector((0., 0., 1.))
    n = norm.normalized()
    e = n.cross(up)
    fv1 = fc - edge.verts[0].co
    fv2 = fc - edge.verts[1].co
    if (fv1.normalized().dot(e) > 0):
        # DO (return fv1, fv2) to get MOBIUS. Also must change call location!
        return fv2, fv1
    # DO (return fv2, fv1) to get MOBIUS. Also must change call location!
    return fv1, fv2

# Find translation vect
def find_local_trans(normal, cm): 
    up = Vector((0., 0., 1.))
    n = normal.normalized()
    e = -n.cross(up)
    e.normalize()
    loc = Vector(((n[0] * cm[0] + n[1] * cm[1] + n[2] * cm[2]), (e[0] * cm[0] + e[1] * cm[1] + e[2] * cm[2]), (up[0] * cm[0] + up[1] * cm[1] + up[2] * cm[2])))
    
    return loc

# Applies staged transforms
def apply_petal_transforms(petal):
    mb = petal.matrix_basis
    if hasattr(petal.data, "transform"):
        petal.data.transform(mb)
    for c in petal.children:
        c.matrix_local = mb @ c.matrix_local
    petal.matrix_basis.identity()
    return

def menu_func(self, context):
    self.layout.operator(ObjectFlowerProcess2.bl_idname)

# store keymaps here to access after registration
addon_keymaps = []

# Register as a menu function
def register():
    bpy.utils.register_class(ObjectFlowerProcess2)
    bpy.types.VIEW3D_MT_object.append(menu_func)

    # handle the keymap
    wm = bpy.context.window_manager
    # Note that in background mode (no GUI available), keyconfigs are not available either,
    # so we have to check this to avoid nasty errors in background case.
    kc = wm.keyconfigs.addon
    if kc:
        km = wm.keyconfigs.addon.keymaps.new(name='Object Mode', space_type='EMPTY')
        kmi = km.keymap_items.new(ObjectFlowerProcess2.bl_idname, 'G', 'PRESS', ctrl=True, shift=True)
        addon_keymaps.append((km, kmi))
        

# Deallocate space from menu if not using
def unregister():
    # Note: when unregistering, it's usually good practice to do it in reverse order you registered.
    # Can avoid strange issues like keymap still referring to operators already unregistered...
    # handle the keymap
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()

    bpy.utils.unregister_class(ObjectFlowerProcess2)
    bpy.types.VIEW3D_MT_object.remove(menu_func)


if __name__ == "__main__":
    register()
