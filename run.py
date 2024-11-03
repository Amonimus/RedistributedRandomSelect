import bpy
import random
from random import randint
import numpy
import time
from math import radians
from threading import Thread
import bmesh
from itertools import product

class RandomSampleOperator(bpy.types.Operator):
    bl_idname: str = "custom.random_sample"
    bl_label: str = "Random Sample Operator"
    _busy: bool = False
    _timer: bpy.types.Timer = None
    
    def __init__(self) -> None:
        self.pool: dict = {}
        self.bars: dict = {}
        self.picks: dict = {}
        self.seq: list = []
        self.size: int = 16
        self.runs: int = 64
        self.done_runs: int = 0

    def execute(self, context: bpy.types.Context) -> dict:
        self.init_data()
        
        #self.make_cube()
        
        wm: bpy.types.WindowManager = context.window_manager
        self._timer = wm.event_timer_add(time_step=0.01, window=context.window)
        wm.modal_handler_add(self)
        
        return {'RUNNING_MODAL'}

    def modal(self, context: bpy.types.Context, event: bpy.types.Event) -> dict:
        context.area.tag_redraw()
        if event.type in {'RIGHTMOUSE', 'ESC'}:
            print("Abort!")
            self.cancel(context)
            return {'CANCELLED'}
        if event.type == 'TIMER':
            if not self._busy:
                self.action_loop()
                self.done_runs += 1
                print(f"Loop: {self.done_runs}")
                if self.done_runs >= self.runs:
                    return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def cancel(self, context: bpy.types.Context) -> dict:
        wm: bpy.types.WindowManager = context.window_manager
        wm.event_timer_remove(self._timer)
        print("Finished!")
        return {'FINISHED'}

    def redraw(self) -> None:
        bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)

    def clear(self) -> None:
        for mesh in bpy.data.meshes:
            bpy.data.meshes.remove(mesh)
        for mat in bpy.data.materials:
            bpy.data.materials.remove(mat)
        for ob in bpy.data.objects:
            ob.select_set(True)
        bpy.ops.object.delete()

    def init_data(self) -> None:
        self.pool = {}
        for i in range(self.size):
            self.pool[str(i)] = 1 / self.size
            self.picks[str(i)] = 0
        self.seq = []

    def make_cube(self) -> bpy.types.Object:
        vertices = [(x, y, z) for x, y, z in product(range(0,1,3), range(0,1,3), range(0,1,3))]
        mesh = bpy.data.meshes.new("CubeMap")
        cube = bpy.data.objects.new("CubeMap", mesh)
        
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bmesh.ops.create_cube(bm, size=1, calc_uvs=False)
        bm.to_mesh(mesh)
        bm.free()

        bpy.context.scene.collection.objects.link(cube)
        bpy.context.view_layer.objects.active = cube
        
        mesh = bpy.data.meshes.new("CubeMap")
        obj = bpy.data.objects.new("CubeMap", mesh)
        
        obj.data.from_pydata(vertices, [], [])
        bpy.context.scene.collection.objects.link(obj)
        bpy.context.view_layer.objects.active = obj
        cube.parent = obj
        obj.instance_type = 'VERTS'
        obj.location = (5, 5, 5)
        return obj

    def create_bar(self, loc: tuple, scale: tuple) -> bpy.types.Object:
        bpy.ops.mesh.primitive_cube_add(location=loc, scale=scale)
        obj: bpy.types.Object = bpy.context.object
        obj.color = (0.0, 1.0, 1.0, 1.0)
        obj.select_set(False)
        return obj
    
    def add_text(self, loc: tuple, text: str, rot: tuple) -> None:
        text_curve: bpy.types.TextCurve = bpy.data.curves.new("message", "FONT")
        text_curve.size = 0.9
        text_object: bpy.types.Object = bpy.data.objects.new("message", text_curve)
        bpy.context.collection.objects.link(text_object)
        text_object.location = loc
        text_object.rotation_euler = (radians(rot[0]), radians(rot[1]), radians(rot[2]))
        text_curve.body = text
        text_curve.extrude = 0.1
    
    def create_label(self, loc: tuple, text) -> None:
        self.add_text((loc[0], loc[1], loc[2]), text, (90, 0, 0))

    def create_output(self) -> None:
        text: str = ','.join(self.seq)
        if len(text) > 64:
            text = text[:70] + '\n' + text[70:]
        self.add_text((0, -3, 0), text, (0, 0, 0))

    def create_chart(self) -> None:
        for p, (k, v) in enumerate(self.pool.items()):
            scale: tuple = (1, 1, 100*v)
            loc: tuple = (p*2.5, 0, scale[2])
            obj: bpy.types.Object = self.create_bar(loc, scale)
            self.bars[str(k)] = obj
            
            label_loc: tuple = (loc[0]-1, loc[1]-1, 2*scale[2])
            text: str = format(v, '.3f')
            self.create_label(label_loc, text)
            
            label_loc: tuple = (loc[0], loc[1]-1, 0)
            text: str = str(p)
            self.create_label(label_loc, text)
        
    def rand_select(self) -> str:
        keys: list = list(self.pool.keys())
        take: str = random.choice(keys)
        self.seq.append(take)
        return take

    def rand_w_select(self) -> str:
        # weighted random sampling with replacement"
        # or can be seen as a variant of "reservoir sampling"
        # or "dynamic weighted sampling." 
        #print("Start run")
        #print(self.pool)
        keys: list = list(self.pool.keys())
        weights: list = list(self.pool.values())
        take_idx: str = numpy.random.choice(keys, 1, False, weights)[0]
        self.seq.append(take_idx)
        self.update_values(take_idx)
        return take_idx

    def update_values(self, take_idx: str) -> None:
        take_val: float = self.pool[take_idx]
        self.pool[take_idx] = 0.0
        for k, v in self.pool.items():
            if k != take_idx:
                self.pool[k] += take_val / (self.size - 1)
                self.picks[k] += 1
    
    def action_loop(self) -> None:
        self._busy = True
        self.clear()
        self.create_chart()
        #self.redraw()
        if self.done_runs == 0:
            self.redraw()
            time.sleep(1)
        #take_idx: str = self.rand_select()
        take_idx: str = self.rand_w_select()
        self.bars[take_idx].color = (1.0, 0.0, 0.0, 1.0)
        self.create_output()
        self.redraw()
        self._busy = False

if __name__ == "__main__":
    bpy.utils.register_class(RandomSampleOperator)
    bpy.ops.custom.random_sample()