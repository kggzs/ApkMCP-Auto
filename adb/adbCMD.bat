@echo off
chcp 65001 > nul
title adb和fastboot 工具
color 3f

echo.          adb和fastboot 工具
echo.-----------------------------------------
echo.         adb和fastboot工具提示：
echo. adb命令：
echo.	adb devices		:列出adb设备
echo.	adb reboot		:重启本设备
echo.	adb reboot bootloader	:进入fastboot模式
echo.	adb reboot recovery	:进入recovery模式
echo.	adb reboot edl		:进入edl模式
echo.
echo. fastboot命令：
echo.	fastboot devices			:列出fastboot设备
echo.	fastboot reboot				:重启本设备
echo.	fastboot reboot-bootloader		:进入fastboot模式
echo.	fastboot flash ^<分区名称^> ^<镜像文件路径^>	:刷写固件
echo.	fastboot oem reboot-^<模式名称^> 		:进入相应模式
echo.	fastboot oem device-info 		:查看设备状态
echo.-----------------------------------------
echo.	第一步  设备进入fastboot模式（重启或音量+电源键）
echo.	第二步  连接USB线，打开本程序会自动加载驱动
echo.	第三步  等待系统自动安装完成，关闭本窗口+拔掉USB线
echo.	第四步  输入下方指令  或手机连接Bugjaeger+双c线：
echo.	fastboot oem set-gpu-preemption 0
echo.	fastboot oem set-androidboot.selinux permissive
echo.	fastboot continue
echo.	第五步  等待系统自动进入完成，拔掉USB线：
echo.-----------------------------------------
echo. 下方输入adb或fastboot命令：
echo.
cd /d "%~dp0"
cmd /k
