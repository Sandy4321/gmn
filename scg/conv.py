from core import *
from deterministic import dispatch_function, glorot_normal, he_normal


class Convolution2d(NodePrototype):
    def __init__(self, input_shape, kernel_size, num_filters, stride=1,
                 padding='SAME', fun=None, init=he_normal,
                 transpose=False):
        NodePrototype.__init__(self)

        self.input_shape = input_shape
        self.kernel_size = kernel_size
        self.num_filters = num_filters
        self.strides = [1, stride, stride, 1]
        self.padding = padding
        self.fun = fun

        self.transpose = transpose
        if self.transpose:
            self.output_shape = [(input_shape[0] - 1) * stride + kernel_size[0],
                                 (input_shape[1] - 1) * stride + kernel_size[1],
                                 num_filters]

        if fun == 'prelu':
            self.p = tf.Variable(tf.random_uniform((self.num_filters,), minval=-0.01, maxval=0.01))

        factor = np.prod(kernel_size)
        if self.transpose:
            self.bias = tf.zeros([self.output_shape[-1]])
            self.filters = init(factor * num_filters, factor * self.input_shape[-1], fun,
                                kernel_size + [num_filters, self.input_shape[-1]])
        else:
            self.bias = tf.zeros([num_filters])
            self.filters = init(factor * self.input_shape[-1], factor * num_filters, fun,
                                kernel_size + [self.input_shape[-1], num_filters])

    def shape(self):
        if self.transpose:
            if self.padding == 'SAME':
                raise NotImplementedError()
            return self.output_shape

        if self.padding == 'VALID':
            sh = [float(self.input_shape[0] - self.kernel_size[0]) / self.strides[1] + 1,
                  float(self.input_shape[1] - self.kernel_size[1]) / self.strides[2] + 1]
            return map(lambda x: int(np.ceil(x)), sh) + [self.num_filters]
        else:
            return [self.input_shape[0], self.input_shape[1], self.num_filters]

    def flow(self, input=None):
        assert input is not None

        batch = tf.shape(input)[0]
        input = tf.reshape(input, tf.pack([batch] + self.input_shape))

        if self.transpose:
            output = tf.nn.conv2d_transpose(input, self.filters, tf.pack([batch] + self.output_shape),
                                            self.strides, self.padding)
        else:
            output = tf.nn.conv2d(input, self.filters, self.strides, self.padding)
        output += self.bias

        args = {}
        if self.fun == 'prelu':
            args['p'] = self.p

        output = dispatch_function(output, self.fun, **args)
        return NodePrototype.flatten(output)


class Padding(NodePrototype):
    def __init__(self, input_shape, paddings):
        NodePrototype.__init__(self)

        self.input_shape = input_shape
        self.paddings = paddings

    def flow(self, input=None):
        assert input is not None
        batch = tf.shape(input)[0]
        x = tf.reshape(input, tf.pack([batch] + self.input_shape))
        x = tf.pad(x, [[0, 0]] + self.paddings)
        return NodePrototype.flatten(x)


class Pooling(NodePrototype):
    def __init__(self, input_shape, kernel_size, strides=[1, 1], padding='VALID', fun='avg'):
        NodePrototype.__init__(self)
        self.input_shape = input_shape
        self.kernel_size = kernel_size
        self.strides = [1] + strides + [1]
        self.padding = padding
        self.fun = fun

    def flow(self, input=None):
        funs = {
            'avg': tf.nn.avg_pool,
            'max': tf.nn.max_pool
        }
        return funs[self.fun](input, self.kernel_size, self.strides, self.padding)