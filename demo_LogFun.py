import time
from LogFun import traced, basicConfig, gzip_file

basicConfig(mode='remote', logtype='normal')


@traced
def addAlpha(x, y):
    a = 0.01
    z = x + a * y
    addAlpha._log('%s + %s * %s', (x, a, y))
    return z


@traced
def multBeta(x):
    multBeta._log('begin multBeta mult %s', x)
    beta = 1
    z = x * beta
    multBeta._log('run multBeta z is %s', z)
    multBeta._log('end multBeta successfully')
    return z


@traced
def function_test():
    begin_time = time.time() * 1000
    a1 = 1
    for i in range(10000):
        a1 = addAlpha(a1, i)
        a1 = multBeta(a1)
    end_time = time.time() * 1000
    print("Duration: %s", (end_time - begin_time))
    return a1


@traced(methods=['add'], exclude=False)
class compute:
    def __init__(self, x):
        self._x = x
        self.__log("initial a compute")

    def add(self, y):
        self._x = self._x + y
        self.__log("add %s + %s", (self._x, y))
        self._x = self.mul(self._x)
        return self._x

    def mul(self, y):
        self._x = self._x * y
        self.__log("mul %s * %s", (self._x, y))
        return self._x


@traced
def class_test():
    c = compute(1)
    c = c.add(1)
    class_test._log('compute is completed')
    return c

# 

if __name__ == '__main__':
    function_test()
    # class_test()
