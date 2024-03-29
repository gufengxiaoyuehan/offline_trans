==========================
Offline transport toolset
==========================
docker-based offline code repository transport toolset,
you must supply a `Dockerfile` in you repository or input
`docker image` name you want transport. ofcause, make sure
docker installed in both your machine.


install
--------
clone this project and run:

.. code-block:: python

    python setup install


usage
------
1. first initiate your image as base by ``offline_trans init <image-name>``
   in you develop machine,
   it will generate two files:

  * `tar.gz` file containes images layers by ``docker save``.
  * `<image name>_layers.json` contains hash information about
     all layers, it also generated by ``offline_trans import`` command.

2. then transport this two file to your offline machine, and export
   use ``offline_trans import <image-name>``, **this will update json file**

3. when image changed in the develop machine, use
   ``offline_trans export <image-name>`` generate diff layers.
   (make sure json file in your workdir or specifile by option.

4. again, transport this two file, and import this like step 2.

test
-----
make sure you have ``docker`` installed, and run:

.. code-block:: python

    python run_nose.py

