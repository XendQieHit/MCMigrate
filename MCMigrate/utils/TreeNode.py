class TreeNode: # 岂可修...Python的多重继承ORM导致这个自己手搓的node几乎排不上用场，呜;w;...
    def __init__(self, name=None):
        self.name = name
        self.children = []

    def add_child(self, child_node):
        self.children.append(child_node)
        return child_node
    
    def get_child(self, name):
        for child in self.children:
            if child.name == name:
                return child
        return None

    def is_leaf(self):
        '''判断是否为叶子节点'''
        return len(self.children) == 0