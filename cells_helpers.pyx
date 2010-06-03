cimport numpy


def get_small_view_fast(self, int x, int y):
    cdef numpy.ndarray[object, ndim=2] values = self.values
    cdef int width = self.width
    cdef int height = self.height
    cdef int dr
    cdef int dc
    cdef int adj_x
    cdef int adj_y


    assert self.values.dtype == object
    ret = []
    get = self.get

    for dr in xrange(-1,2):
        for dc in xrange(-1,2):
            if not dr and not dc:
                continue
            adj_x = x + dr
            if not 0 <= adj_x < width:
                continue
            adj_y = y + dc
            if not 0 <= adj_y < height:
                continue
            a = values[adj_x, adj_y]
            if a is not None:
                ret.append(a.get_view())
    return ret
