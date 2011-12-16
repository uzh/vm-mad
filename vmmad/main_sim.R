#R

# R --no-save < main_sim.R

# get in the data
s<-read.table("main_sim.txt",sep=',')

# open plot device
pdf("main_sim.pdf", 19,12)

# have fun
plot(s[,1],s[,2],
    sub='grey number of idle vms; gree running hosts; red pendig jobs',
    type='l',
    xlab='time',
    ylab='number of ...',
    col='red'); 

lines(s[,1],s[,3],col='green'); 
lines(s[,1],s[,4],col='grey')

# close plot device
dev.off()
