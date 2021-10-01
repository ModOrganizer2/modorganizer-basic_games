# -*- encoding: utf-8 -*-


class IVec3:
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

    def __str__(self) -> str:
        return f"{self.x}, {self.y}, {self.z}"

    def set(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z


class IVec4(IVec3):
    def __init__(self, x, y, z, w):
        super().__init__(x, y, z)
        self.w = w

    def __str__(self) -> str:
        return f"{self.x}, {self.y}, {self.z}, f{self.w}"

    def set(self, x, y, z, w):
        super().set(x, y, z)
        self.w = w


class IFlag:
    def __init__(self, flag: int):
        self._flag = flag

    def __str__(self) -> str:
        return str(self._flag)

    def assign(self, mask):
        self._flag = mask

    def has(self, mask) -> bool:
        return bool((self._flag & mask) == mask)

    def set(self, mask):
        self._flag |= mask

    def remove(self, mask):
        self._flag &= ~mask
