import time
import gzip
import logging

# logging.basicConfig(level=logging.DEBUG,
#                     format='%(asctime)s %(process)d %(pathname)s %(filename)s %(lineno)d %(funcName)s %(message)s',
#                     datefmt='%Y %H:%M:%S')

logging.basicConfig(filename='logging.log',
                    filemode='a',
                    level=logging.DEBUG,
                    format='%(asctime)s %(process)d %(pathname)s %(filename)s %(lineno)d %(funcName)s %(message)s',
                    datefmt='%Y %H:%M:%S')


def gzip_file(filename):
    with open(filename, 'rb') as f_in:
        with gzip.open(filename.split('.')[0] + '.gz', 'wb') as f_out:
            f_out.writelines(f_in)


def addAlpha(x, y):
    logging.info((x, y))
    alpha = 0.01
    z = x + alpha * y
    logging.info(('step 1 begin addAlpha add %s and %s') % (x, y))
    if z < 0:
        logging.info('z is less than 0')
    logging.info(('step 2 run addAlpha z is %s') % z)
    logging.info('step 3 end addAlpha successfully')
    logging.info(('return %s') % z)
    return z


def multBeta(x):
    logging.info(x)
    logging.info(('step 1 begin multBeta mult %s') % x)
    beta = 1
    z = x * beta
    logging.info(('step 2 run multBeta z is %s') % z)
    logging.info('step 3 end multBeta successfully')
    logging.info(('return %s') % z)
    return z


def function_test():
    logging.info("None")
    begin_time = time.time() * 1000
    a1 = 1
    for i in range(10000):
        try:
            a1 = addAlpha(a1, i)
            a1 = multBeta(a1)
        except Exception as e:
            pass
    end_time = time.time() * 1000
    print("Duration: %s", (end_time - begin_time))
    logging.info(('return %s') % a1)
    return a1


if __name__ == '__main__':
    function_test()
    gzip_file('logging.log')
