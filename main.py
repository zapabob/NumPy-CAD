import sys
import numpy as np
from PyQt5.QtWidgets import QApplication, QMainWindow, QAction, QFileDialog, QVBoxLayout, QWidget, QPushButton, QMessageBox
from PyQt5.QtOpenGL import QGLWidget
from OpenGL.GL import *
from OpenGL.GLU import *
import bpy
import vrm2py

class Mesh:
    def __init__(self, vertices, faces):
        self.vertices = vertices
        self.faces = faces

    def add_mesh(self, other_mesh):
        try:
            offset = len(self.vertices)
            new_vertices = np.vstack((self.vertices, other_mesh.vertices))
            new_faces = np.vstack((self.faces, other_mesh.faces + offset))
            return Mesh(new_vertices, new_faces)
        except Exception as e:
            print(f"Error in add_mesh: {e}")
            return None

    def merge_vertices(self, threshold=0.01):
        try:
            unique_vertices = []
            indices = []
            for vertex in self.vertices:
                for i, unique_vertex in enumerate(unique_vertices):
                    if np.linalg.norm(vertex - unique_vertex) < threshold:
                        indices.append(i)
                        break
                else:
                    unique_vertices.append(vertex)
                    indices.append(len(unique_vertices) - 1)
            unique_vertices = np.array(unique_vertices)
            new_faces = np.array([[indices[vertex] for vertex in face] for face in self.faces])
            return Mesh(unique_vertices, new_faces)
        except Exception as e:
            print(f"Error in merge_vertices: {e}")
            return None

def create_cube(size):
    vertices = np.array([
        [-size, -size, -size],
        [ size, -size, -size],
        [ size,  size, -size],
        [-size,  size, -size],
        [-size, -size,  size],
        [ size, -size,  size],
        [ size,  size,  size],
        [-size,  size,  size]
    ])
    faces = np.array([
        [0, 1, 2, 3],
        [4, 5, 6, 7],
        [0, 1, 5, 4],
        [2, 3, 7, 6],
        [0, 3, 7, 4],
        [1, 2, 6, 5]
    ])
    return Mesh(vertices, faces)

def create_sphere(radius, segments):
    vertices = []
    faces = []
    for i in range(segments):
        lat0 = np.pi * (-0.5 + float(i) / segments)
        z0 = np.sin(lat0)
        zr0 = np.cos(lat0)
        lat1 = np.pi * (-0.5 + float(i + 1) / segments)
        z1 = np.sin(lat1)
        zr1 = np.cos(lat1)
        for j in range(segments):
            lng = 2 * np.pi * float(j) / segments
            x = np.cos(lng)
            y = np.sin(lng)
            vertices.append([x * zr0 * radius, y * zr0 * radius, z0 * radius])
            vertices.append([x * zr1 * radius, y * zr1 * radius, z1 * radius])
    for i in range(0, len(vertices) - segments * 2, 2):
        faces.append([i, i + 1, i + segments * 2 + 1, i + segments * 2])
    return Mesh(np.array(vertices), np.array(faces))

def create_cylinder(radius, height, segments):
    vertices = []
    faces = []
    for i in range(segments):
        angle = 2 * np.pi * i / segments
        x = np.cos(angle) * radius
        y = np.sin(angle) * radius
        vertices.append([x, y, 0])
        vertices.append([x, y, height])
    for i in range(0, segments * 2, 2):
        faces.append([i, (i + 2) % (segments * 2), (i + 3) % (segments * 2), i + 1])
    return Mesh(np.array(vertices), np.array(faces))

def create_torus(inner_radius, outer_radius, segments, sides):
    vertices = []
    faces = []
    for i in range(segments):
        for j in range(sides):
            angle = 2 * np.pi * i / segments
            theta = 2 * np.pi * j / sides
            x = (outer_radius + inner_radius * np.cos(theta)) * np.cos(angle)
            y = (outer_radius + inner_radius * np.cos(theta)) * np.sin(angle)
            z = inner_radius * np.sin(theta)
            vertices.append([x, y, z])
    for i in range(segments):
        for j in range(sides):
            faces.append([
                i * sides + j,
                i * sides + (j + 1) % sides,
                ((i + 1) % segments) * sides + (j + 1) % sides,
                ((i + 1) % segments) * sides + j
            ])
    return Mesh(np.array(vertices), np.array(faces))

class GLWidget(QGLWidget):
    def __init__(self, parent=None):
        super(GLWidget, self).__init__(parent)
        self.meshes = []
        self.combined_mesh = None

    def initializeGL(self):
        glEnable(GL_DEPTH_TEST)

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        gluLookAt(0, 0, 5, 0, 0, 0, 0, 1, 0)

        if self.combined_mesh:
            self.draw_mesh(self.combined_mesh)

    def resizeGL(self, width, height):
        glViewport(0, 0, width, height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45, width / height, 1, 100)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

    def draw_mesh(self, mesh):
        try:
            glBegin(GL_QUADS)
            for face in mesh.faces:
                for vertex in face:
                    glVertex3fv(mesh.vertices[vertex])
            glEnd()
        except Exception as e:
            print(f"Error in draw_mesh: {e}")

    def add_mesh(self, mesh):
        self.meshes.append(mesh)
        try:
            if len(self.meshes) > 1:
                self.combined_mesh = self.meshes[0]
                for m in self.meshes[1:]:
                    self.combined_mesh = self.combined_mesh.add_mesh(m)
                self.combined_mesh = self.combined_mesh.merge_vertices()
        except Exception as e:
            print(f"Error in add_mesh: {e}")
        self.update()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle('VRChat 空間デザインおよびアバター制作アプリケーション')
        self.setGeometry(100, 100, 800, 600)
        
        self.glWidget = GLWidget(self)
        self.setCentralWidget(self.glWidget)
        
        menubar = self.menuBar()
        fileMenu = menubar.addMenu('ファイル')
        
        add_cube_action = QAction('キューブを追加', self)
        add_cube_action.triggered.connect(self.add_cube)
        fileMenu.addAction(add_cube_action)
        
        add_sphere_action = QAction('球体を追加', self)
        add_sphere_action.triggered.connect(self.add_sphere)
        fileMenu.addAction(add_sphere_action)
        
        add_cylinder_action = QAction('円柱を追加', self)
        add_cylinder_action.triggered.connect(self.add_cylinder)
        fileMenu.addAction(add_cylinder_action)
        
        add_torus_action = QAction('トーラスを追加', self)
        add_torus_action.triggered.connect(self.add_torus)
        fileMenu.addAction(add_torus_action)
        
        load_vrm_action = QAction('VRMを読み込み', self)
        load_vrm_action.triggered.connect(self.load_vrm)
        fileMenu.addAction(load_vrm_action)
        
        add_armature_action = QAction('アーマチュアを追加', self)
        add_armature_action.triggered.connect(self.add_armature)
        fileMenu.addAction(add_armature_action)
        
        export_fbx_action = QAction('FBXとしてエクスポート', self)
        export_fbx_action.triggered.connect(self.export_fbx)
        fileMenu.addAction(export_fbx_action)
        
        combine_button = QPushButton('メッシュを結合', self)
        combine_button.clicked.connect(self.combine_meshes)
        menubar.setCornerWidget(combine_button, Qt.TopRightCorner)
        
        # Custom tool import
        import_tool_action = QAction('カスタムツールをインポート', self)
        import_tool_action.triggered.connect(self.import_custom_tool)
        fileMenu.addAction(import_tool_action)

        # Interactive tutorial
        tutorial_action = QAction('インタラクティブチュートリアル', self)
        tutorial_action.triggered.connect(self.show_tutorial)
        fileMenu.addAction(tutorial_action)

    def add_cube(self):
        try:
            cube = create_cube(1.0)
            if len(self.glWidget.meshes) > 0:
                cube.vertices += np.array([2.0 * len(self.glWidget.meshes), 0.0, 0.0])
            self.glWidget.add_mesh(cube)
        except Exception as e:
            print(f"Error in add_cube: {e}")

    def add_sphere(self):
        try:
            sphere = create_sphere(1.0, 32)
            if len(self.glWidget.meshes) > 0:
                sphere.vertices += np.array([2.0 * len(self.glWidget.meshes), 0.0, 0.0])
            self.glWidget.add_mesh(sphere)
        except Exception as e:
            print(f"Error in add_sphere: {e}")

    def add_cylinder(self):
        try:
            cylinder = create_cylinder(0.5, 2.0, 32)
            if len(self.glWidget.meshes) > 0:
                cylinder.vertices += np.array([2.0 * len(self.glWidget.meshes), 0.0, 0.0])
            self.glWidget.add_mesh(cylinder)
        except Exception as e:
            print(f"Error in add_cylinder: {e}")

    def add_torus(self):
        try:
            torus = create_torus(0.2, 0.8, 32, 16)
            if len(self.glWidget.meshes) > 0:
                torus.vertices += np.array([2.0 * len(self.glWidget.meshes), 0.0, 0.0])
            self.glWidget.add_mesh(torus)
        except Exception as e:
            print(f"Error in add_torus: {e}")

    def load_vrm(self):
        try:
            filepath, _ = QFileDialog.getOpenFileName(self, "Open VRM", "", "VRM Files (*.vrm);;All Files (*)")
            if filepath:
                vrm2py.load_vrm(filepath)
                bpy.ops.object.select_all(action='DESELECT')
                for obj in bpy.data.objects:
                    if obj.type == 'MESH':
                        obj.select_set(True)
                bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
                QMessageBox.information(self, "読み込み完了", "VRMファイルが読み込まれました。")
        except Exception as e:
            print(f"Error in load_vrm: {e}")
            QMessageBox.critical(self, "読み込みエラー", "VRMファイルの読み込み中にエラーが発生しました。")

    def add_armature(self):
        try:
            self.create_armature()
            avatar_mesh = self.create_avatar_mesh()
            armature = bpy.data.objects["AvatarArmature"]
            self.parent_to_armature(avatar_mesh, armature)
        except Exception as e:
            print(f"Error in add_armature: {e}")

    def combine_meshes(self):
        try:
            if self.glWidget.combined_mesh:
                print("Combined vertices:\n", self.glWidget.combined_mesh.vertices)
                print("Combined faces:\n", self.glWidget.combined_mesh.faces)
                self.glWidget.update()
        except Exception as e:
            print(f"Error in combine_meshes: {e}")

    def export_fbx(self):
        try:
            filepath, _ = QFileDialog.getSaveFileName(self, "Save FBX", "", "FBX Files (*.fbx);;All Files (*)")
            if filepath:
                bpy.ops.object.select_all(action='DESELECT')
                bpy.ops.object.select_all(action='SELECT')
                bpy.ops.export_scene.fbx(filepath=filepath)
                QMessageBox.information(self, "エクスポート完了", "FBXファイルとしてエクスポートされました。")
        except Exception as e:
            print(f"Error in export_fbx: {e}")
            QMessageBox.critical(self, "エクスポートエラー", "エクスポート中にエラーが発生しました。")

    def create_armature(self):
        bpy.ops.object.armature_add(enter_editmode=True, align='WORLD', location=(0, 0, 0), scale=(1, 1, 1))
        armature = bpy.context.object
        armature.name = "AvatarArmature"

        bpy.ops.armature.bone_primitive_add()
        bone = armature.data.edit_bones[-1]
        bone.name = "Spine"
        bone.head = (0, 0, 0)
        bone.tail = (0, 0, 1)

        bpy.ops.object.mode_set(mode='OBJECT')

    def create_avatar_mesh(self):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=1, location=(0, 0, 0))
        avatar_mesh = bpy.context.object
        avatar_mesh.name = "AvatarMesh"
        
        mat = bpy.data.materials.new(name="AvatarMaterial")
        avatar_mesh.data.materials.append(mat)
        
        return avatar_mesh

    def parent_to_armature(self, mesh, armature):
        modifier = mesh.modifiers.new(name="ArmatureMod", type='ARMATURE')
        modifier.object = armature
        mesh.parent = armature

    def import_custom_tool(self):
        try:
            filepath, _ = QFileDialog.getOpenFileName(self, "Import Custom Tool", "", "Python Files (*.py);;All Files (*)")
            if filepath:
                with open(filepath, 'r') as file:
                    exec(file.read())
                QMessageBox.information(self, "インポート完了", "カスタムツールがインポートされました。")
        except Exception as e:
            print(f"Error in import_custom_tool: {e}")
            QMessageBox.critical(self, "インポートエラー", "カスタムツールのインポート中にエラーが発生しました。")

    def show_tutorial(self):
        try:
            QMessageBox.information(self, "チュートリアル", "インタラクティブチュートリアルの開始")
            # インタラクティブチュートリアルの実装
        except Exception as e:
            print(f"Error in show_tutorial: {e}")

if __name__ == '__main__':
    try:
        app = QApplication([])
        window = MainWindow()
        window.show()
        app.exec_()
    except Exception as e:
        print(f"Error in main: {e}")
