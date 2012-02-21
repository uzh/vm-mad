#! /usr/bin/Rscript
#
# Usage: plot_workload.R workload.csv output.pdf
#

## set plot aspect characteristics
my.legend <- c('pending jobs', 'running jobs', 'started nodes', 'idle nodes');
my.col    <- c('red',          'blue',         'cyan',          'grey');
my.lty    <- c('solid',        'solid',        'solid',         'solid');
my.lwd    <- c(1,              1,              1,               1);

# read command-line args
args <- commandArgs(trailingOnly=TRUE)
input <- args[1]
output <- args[2]

# get in the data
dat <- read.table(input, sep=',')

# auxiliary function
mktime <- function (epoch) {
    as.POSIXct(epoch, origin='1970-01-01');
}

do_plot <- function (dat) {
    plot(dat[,1], dat[,1],
         ylim=c(0, max(dat[,2], dat[,3], dat[,4], dat[,5])),
         type='n',
         xlab='Time',
         ylab='Number of ...',
         axes=F);
    for (i in 1:4) {
        lines(dat[,1], dat[,(i+1)], 
              col=my.col[i], lwd=my.lwd[i], lty=my.lty[i]);
    };
    legend('topright', inset=0.05, my.legend,
           col=my.col, lty=my.lty, lwd=my.lwd, title="Legend");

    idx<-seq(1 , length(dat[,1]), length=10);
    axis(1, idx, round(dat[idx,1]/60));
    axis(3, idx, round(dat[idx,1]));
    axis(2);
    box();
}


# PDF plot
pdf(paste(output, ".pdf", sep=''), 10, 7)
do_plot(dat)
dev.off()

# EPS plot
setEPS()
postscript(paste(output, ".eps", sep=''), height=7, width=10)
do_plot(dat)
dev.off()

# exit without saving
q("no")
