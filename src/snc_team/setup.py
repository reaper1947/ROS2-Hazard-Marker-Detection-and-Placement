# from setuptools import find_packages, setup
# from glob import glob
# import os

# package_name = 'snc_team'

# setup(
#     name=package_name,
#     version='1.0.0',
#     packages=find_packages(exclude=['test']),
#     data_files=[
#         ('share/ament_index/resource_index/packages',['resource/' + package_name]),
#         (os.path.join('share', package_name, 'launch'), glob('launch/*.launch')),
#         (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
#         (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
#         ('share/' + package_name, ['package.xml']),
#     ],
#     install_requires=['setuptools'],
#     zip_safe=True,
#     maintainer='Your Name Here',
#     maintainer_email='your.email@student.rmit.edu.au',
#     description='Template package structure for PAR coursework',
#     license='RMIT IP - Not for distribution',
#     # tests_require=['pytest'],
#     entry_points={
#         'console_scripts': [
#             f"cmd_vel = {package_name}.cmd_vel:main",
#         ],
#     },
# )

from setuptools import find_packages, setup
from glob import glob
import os

package_name = "snc_team"

setup(
    name=package_name,
    version="1.0.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        (os.path.join("share", package_name, "launch"), glob("launch/*.launch.py")),
        (os.path.join("share", package_name, "config"), glob("config/*.yaml")),
        ("share/" + package_name, ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Your Name",
    maintainer_email="your.email@student.rmit.edu.au",
    description="SNC Team - Search and Navigation Challenge",
    license="RMIT IP - Not for distribution",
    entry_points={
        "console_scripts": [
            "cmd_vel = snc_team.cmd_vel:main",
            "hazard_detector = snc_team.hazard_detector:main",
        ],
    },
)
