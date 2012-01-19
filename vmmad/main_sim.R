# main_sim.R
#
# Run as follows:
#
#     main_sim.R --no-save < main_sim.R
#

# get in the data
s<-read.table("main_sim.txt",sep=',')

# open plot device
pdf("main_sim.pdf", 19,12)


op<-par(mfrow=c(2,2))


# have fun
plot(s[,1],s[,2],
    sub='red is pending jobs; green is running jobs; purple is started VMs; grey is idle VMs',
    type='l',
    xlab='time',
    ylab='number of ...',
    axes=F,
    col='red'); 
lines(s[,1],s[,3],col='green'); # running jobs
lines(s[,1],s[,4],col='purple');# started VMs
lines(s[,1],s[,5],col='grey');  # idle VMs

idx<-seq(1 , length(s[,1]),  length=10)
axis(1, idx, round(s[idx,1]/60))
axis(3, idx, round(s[idx,1]))
axis(2)
box()

# close plot device
dev.off()
