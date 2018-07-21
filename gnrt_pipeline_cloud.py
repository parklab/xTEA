import os
from subprocess import *
from optparse import OptionParser


####
def gnrt_script_head():
    s_head = "#!/bin/bash\n\n"
    return s_head


# load in the parameter file or the configuration file
def load_par_config(sf_par_config):
    # by default, SF_FLANK is set to null, as Alu no need for SF_FLANK, as we don't check transduction for Alu
    l_pars = []
    with open(sf_par_config) as fin_par_config:
        for line in fin_par_config:
            if len(line) > 0 and line[0] == "#":
                continue
            fields = line.split()
            l_pars.append((fields[0], fields[1]))
    return l_pars


# gnrt pars
def gnrt_parameters(l_pars):
    s_pars = ""
    for rcd in l_pars:
        sid = rcd[0]
        svalue = str(rcd[1])
        sline = sid + "=" + svalue + "\n"
        s_pars += sline
    return s_pars


# grnt calling steps
def gnrt_calling_command(iclip_c, iclip_rp, idisc_c, iflt_clip, iflt_disc, ncores, iflk_len, min_tei_len, iflag):
    sclip_step = "python ${{XTEA_PATH}}\"x_TEA_main.py\" -C -i ${{BAM_LIST}} --lc {0} --rc {1} --cr {2}  " \
                 "-r ${{L1_COPY_WITH_FLANK}}  -a ${{ANNOTATION}} --ref ${{REF}} -p ${{TMP}} " \
                 "-o ${{PREFIX}}\"candidate_list_from_clip.txt\"  -n {3}\n".format(iclip_c, iclip_c, iclip_rp, ncores)
    sdisc_step = "python ${{XTEA_PATH}}\"x_TEA_main.py\"  -D -i ${{PREFIX}}\"candidate_list_from_clip.txt\" --nd {0} " \
                 "--ref ${{REF}} -a ${{ANNOTATION}} -b ${{BAM_LIST}} -p ${{TMP}} " \
                 "-o ${{PREFIX}}\"candidate_list_from_disc.txt\" -n {1}\n".format(idisc_c, ncores)
    sbarcode_step = "python ${{XTEA_PATH}}\"x_TEA_main.py\" -B -i ${{PREFIX}}\"candidate_list_from_disc.txt\" --nb 400 " \
                    "--ref ${{REF}} -a ${{ANNOTATION}} -b ${{BAM1}} -d ${{BARCODE_BAM}} -p ${{TMP}} " \
                    "-o ${{PREFIX}}\"candidate_list_barcode.txt\" -n {0}\n".format(ncores)
    sfilter_10x = "python ${{XTEA_PATH}}\"x_TEA_main.py\" -N --cr {0} --nd {1} -b ${{BAM_LIST}} -p ${{TMP_CNS}} " \
                  "--fflank ${{SF_FLANK}} --flklen {2} -n {3} -i ${{PREFIX}}\"candidate_list_barcode.txt\" " \
                  "-r ${{L1_CNS}} --ref ${{REF}} -a ${{ANNOTATION}} " \
                  "-o ${{PREFIX}}\"candidate_disc_filtered_cns.txt\"\n".format(iflt_clip, iflt_disc, iflk_len, ncores)
    s_filter = "python ${{XTEA_PATH}}\"x_TEA_main.py\" -N --cr {0} --nd {1} -b ${{BAM_LIST}} -p ${{TMP_CNS}} " \
               "--fflank ${{SF_FLANK}} --flklen {2} -n {3} -i ${{PREFIX}}\"candidate_list_from_disc.txt\" " \
               "-r ${{L1_CNS}} --ref ${{REF}} -a ${{ANNOTATION}} " \
               "-o ${{PREFIX}}\"candidate_disc_filtered_cns.txt\"\n".format(iflt_clip, iflt_disc, iflk_len, ncores)
    sf_collect = "python ${{XTEA_PATH}}\"x_TEA_main.py\" -E --nb 500 -b ${{BAM1}} -d ${{BARCODE_BAM}} --ref ${{REF}} " \
                 "-i ${{PREFIX}}\"candidate_disc_filtered_cns.txt\" -p ${{TMP}} -a ${{ANNOTATION}} -n {0} " \
                 "--flklen {1}\n".format(ncores, iflk_len)
    sf_asm = "python ${{XTEA_PATH}}\"x_TEA_main.py\" -A -L -p ${{TMP}} --ref ${{REF}} -n {0} " \
             "-i ${{PREFIX}}\"candidate_disc_filtered_cns.txt\"\n".format(ncores)
    sf_alg_ctg = "python ${{XTEA_PATH}}\"x_TEA_main.py\" -M -i ${{PREFIX}}\"candidate_disc_filtered_cns.txt\" " \
                 "--ref ${{REF}} -n {0} -p ${{TMP}} -r ${{L1_CNS}} " \
                 "-o ${{PREFIX}}\"candidate_list_asm.txt\"\n".format(ncores)
    sf_mutation = "python ${{XTEA_PATH}}\"x_TEA_main.py\" -I -p ${{TMP}} -n {0} " \
                  "-i ${{PREFIX}}\"candidate_disc_filtered_cns.txt\" -r ${{L1_CNS}} " \
                  "--teilen {1} -o ${{PREFIX}}\"internal_snp.vcf.gz\"\n".format(ncores, min_tei_len)

    ####
    s_cmd = ""
    if iflag & 1 == 1:
        s_cmd += sclip_step
    if iflag & 2 == 2:
        s_cmd += sdisc_step
    if iflag & 4 == 4:
        s_cmd += sbarcode_step
    if iflag & 8 == 8:
        s_cmd += sfilter_10x
    if iflag & 16 == 16:
        s_cmd += s_filter
    if iflag & 32 == 32:
        s_cmd += sf_collect
    if iflag & 64 == 64:
        s_cmd += sf_asm
    if iflag & 128 == 128:
        s_cmd += sf_alg_ctg
    if iflag & 256 == 256:
        s_cmd += sf_mutation
    return s_cmd


####

####gnrt the whole pipeline
def gnrt_pipelines(s_head, s_libs, s_calling_cmd, sf_id, sf_bams, sf_bams_10X, sf_working_folder, sf_sbatch_sh):
    if sf_working_folder[-1] != "/":
        sf_working_folder += "/"

    m_id = {}
    with open(sf_id) as fin_id:
        for line in fin_id:
            sid = line.rstrip()
            m_id[sid] = 1
            sf_folder = sf_working_folder + sid  # first creat folder
            if os.path.exists(sf_folder) == True:
                continue
            cmd = "mkdir {0}".format(sf_folder)
            Popen(cmd, shell=True, stdout=PIPE).communicate()
            # create the temporary folders
            cmd = "mkdir {0}".format(sf_folder + "/tmp")
            Popen(cmd, shell=True, stdout=PIPE).communicate()
            cmd = "mkdir {0}".format(sf_folder + "/tmp/clip")
            Popen(cmd, shell=True, stdout=PIPE).communicate()
            cmd = "mkdir {0}".format(sf_folder + "/tmp/cns")
            Popen(cmd, shell=True, stdout=PIPE).communicate()
    m_bams = {}
    if sf_bams != "null":
        with open(sf_bams) as fin_bams:
            for line in fin_bams:
                fields = line.split()
                sid = fields[0]
                s_bam = fields[1]
                m_bams[sid] = s_bam

    m_bams_10X = {}
    if sf_bams_10X != "null":
        with open(sf_bams_10X) as fin_bams_10X:
            for line in fin_bams_10X:
                fields = line.split()
                sid = fields[0]
                if sid not in m_id:
                    continue
                s_bam = fields[1]
                s_barcode_bam = fields[2]
                m_bams_10X[sid] = s_bam

                # soft-link the bams
                sf_10X_bam = sf_working_folder + sid + "/10X_phased_possorted_bam.bam"
                if os.path.isfile(sf_10X_bam) == False:
                    cmd = "ln -s {0} {1}".format(s_bam, sf_10X_bam)
                    Popen(cmd, shell=True, stdout=PIPE).communicate()

                sf_10X_barcode_bam = sf_working_folder + sid + "/10X_barcode_indexed.sorted.bam"
                if os.path.isfile(sf_10X_barcode_bam) == False:
                    cmd = "ln -s {0} {1}".format(s_barcode_bam, sf_10X_barcode_bam)  #
                    Popen(cmd, shell=True, stdout=PIPE).communicate()
                # soft-link the bai
                sf_10X_bai = sf_working_folder + sid + "/10X_phased_possorted_bam.bam.bai"
                if os.path.isfile(sf_10X_bai) == False:
                    cmd = "ln -s {0} {1}".format(s_bam + ".bai", sf_10X_bai)
                    Popen(cmd, shell=True, stdout=PIPE).communicate()

                sf_10X_barcode_bai = sf_working_folder + sid + "/10X_barcode_indexed.sorted.bam.bai"
                if os.path.isfile(sf_10X_barcode_bai) == False:
                    cmd = "ln -s {0} {1}".format(s_barcode_bam + ".bai", sf_10X_barcode_bai)
                    Popen(cmd, shell=True, stdout=PIPE).communicate()
                    ####
    with open(sf_sbatch_sh, "w") as fout_sbatch:
        fout_sbatch.write("#!/bin/bash\n\n")
        for sid in m_id:
            sf_folder = sf_working_folder + sid + "/"
            if os.path.exists(sf_folder) == False:
                continue

            ####gnrt the bam list file
            sf_bam_list = sf_folder + "bam_list.txt"
            with open(sf_bam_list, "w") as fout_bam_list:
                if sid in m_bams:
                    fout_bam_list.write(m_bams[sid] + "\n")
                if sid in m_bams_10X:
                    fout_bam_list.write(m_bams_10X[sid] + "\n")

            ####gnrt the pipeline file
            sf_out_sh = sf_folder + "run_xTEA_pipeline.sh"
            with open(sf_out_sh, "w") as fout_sh:  ###gnrt the pipeline file
                fout_sh.write(s_head)
                s_prefix = "PREFIX={0}\n".format(sf_folder)
                fout_sh.write(s_prefix)
                fout_sh.write("############\n")
                fout_sh.write("############\n")
                fout_sh.write(s_libs)
                fout_sh.write("############\n")
                fout_sh.write("############\n")
                fout_sh.write(s_calling_cmd)
            ####
            scmd = "sbatch < {0}\n".format(sf_out_sh)
            fout_sbatch.write(scmd)


def write_to_config(sf_anno, sf_ref, sf_copy_with_flank, sf_flank, sf_cns, sf_xtea, s_bl, s_bam1, s_bc_bam,
                    s_tmp, s_tmp_clip, s_tmp_cns, sf_config):
    with open(sf_config, "w") as fout_L1:
        fout_L1.write(sf_anno)
        fout_L1.write(sf_ref)
        fout_L1.write(sf_copy_with_flank)
        fout_L1.write(sf_flank)
        fout_L1.write(sf_cns)
        fout_L1.write(sf_xtea)
        fout_L1.write(s_bl)
        fout_L1.write(s_bam1)
        fout_L1.write(s_bc_bam)
        fout_L1.write(s_tmp)
        fout_L1.write(s_tmp_clip)
        fout_L1.write(s_tmp_cns)


def gnrt_lib_config(sf_folder_rep, sf_ref, sf_folder_xtea, sf_config_prefix):
    if sf_folder_rep[-1] != "/":
        sf_folder_rep += "/"
    if sf_folder_xtea[-1] != "/":
        sf_folder_xtea += "/"
    if sf_config_prefix[-1] != "/":
        sf_config_prefix += "/"

    s_bl = "BAM_LIST ${PREFIX}\"bam_list.txt\"\n"
    s_bam1 = "BAM1 ${PREFIX}\"10X_phased_possorted_bam.bam\"\n"
    s_bc_bam = "BARCODE_BAM ${PREFIX}\"10X_barcode_indexed.sorted.bam\"\n"
    s_tmp = "TMP ${PREFIX}\"tmp/\"\n"
    s_tmp_clip = "TMP_CLIP ${PREFIX}\"tmp/clip/\"\n"
    s_tmp_cns = "TMP_CNS ${PREFIX}\"tmp/cns/\"\n"
    sf_ref = "REF " + sf_ref + "\n"
    sf_xtea = "XTEA_PATH " + sf_folder_xtea + "\n"

    # for L1
    sf_config_L1 = sf_config_prefix + "_L1.config"
    sf_anno = "ANNOTATION " + sf_folder_rep + "LINE/hg19/hg19_L1_larger2K_with_all_L1HS.out\n"
    sf_copy_with_flank = "L1_COPY_WITH_FLANK " + sf_folder_rep + "LINE/hg19/hg19_L1HS_copies_larger_5K_with_flank.fa\n"
    sf_flank = "SF_FLANK " + sf_folder_rep + "LINE/hg19/hg19_FL_L1_flanks_3k.fa\n"
    sf_cns = "L1_CNS " + sf_folder_rep + "consensus/LINE1.fa\n"
    write_to_config(sf_anno, sf_ref, sf_copy_with_flank, sf_flank, sf_cns, sf_xtea, s_bl, s_bam1, s_bc_bam,
                    s_tmp, s_tmp_clip, s_tmp_cns, sf_config_L1)

    #### for Alu
    sf_config_L1 = sf_config_prefix + "_Alu.config"
    sf_anno = "ANNOTATION " + sf_folder_rep + "Alu/hg19/hg19_AluYabc.fa.out\n"
    sf_copy_with_flank = "L1_COPY_WITH_FLANK " + sf_folder_rep + "Alu/hg19/hg19_AluJabc_copies_with_flank.fa\n"
    sf_flank = "SF_FLANK null\n"
    sf_cns = "L1_CNS " + sf_folder_rep + "consensus/ALU.fa\n"
    write_to_config(sf_anno, sf_ref, sf_copy_with_flank, sf_flank, sf_cns, sf_xtea, s_bl, s_bam1, s_bc_bam,
                    s_tmp, s_tmp_clip, s_tmp_cns, sf_config_L1)

    ####for SVA
    sf_config_L1 = sf_config_prefix + "_SVA.config"
    sf_anno = "ANNOTATION " + sf_folder_rep + "SVA/hg19/hg19_SVA.out\n"
    sf_copy_with_flank = "L1_COPY_WITH_FLANK " + sf_folder_rep + "SVA/hg19/hg19_SVA_copies_with_flank.fa\n"
    sf_flank = "SF_FLANK " + sf_folder_rep + "SVA/hg19/hg19_FL_SVA_flanks_3k.fa\n"
    sf_cns = "L1_CNS " + sf_folder_rep + "consensus/SVA.fa\n"
    write_to_config(sf_anno, sf_ref, sf_copy_with_flank, sf_flank, sf_cns, sf_xtea, s_bl, s_bam1, s_bc_bam,
                    s_tmp, s_tmp_clip, s_tmp_cns, sf_config_L1)

####
def parse_option():
    parser = OptionParser()
    parser.add_option("-i", "--id", dest="id",
                      help="sample id list file ", metavar="FILE")
    parser.add_option("-a", "--par", dest="parameters",
                      help="parameter file ", metavar="FILE")
    parser.add_option("-l", "--lib", dest="lib",
                      help="TE lib config file ", metavar="FILE")
    parser.add_option("-b", "--bam", dest="bam",
                      help="Input bam file", metavar="FILE")

    parser.add_option("-p", "--path", dest="wfolder", type="string",
                      help="Working folder")
    parser.add_option("-n", "--cores", dest="cores", type="int",
                      help="number of cores")
    parser.add_option("-r", "--ref", dest="ref", type="string",
                      help="reference genome")
    parser.add_option("-x", "--xtea", dest="xtea", type="string",
                      help="xTEA folder")

    parser.add_option("-f", "--flag", dest="flag", type="int",
                      help="Flag indicates which step to run (1-clip, 2-disc, 4-barcode, 8-xfilter, 16-filter, 32-asm)")

    parser.add_option("--flklen", dest="flklen", type="int",
                      help="flank region file")
    parser.add_option("--nclip", dest="nclip", type="int",
                      help="cutoff of minimum # of clipped reads")
    parser.add_option("--cr", dest="cliprep", type="int",
                      help="cutoff of minimum # of clipped reads whose mates map in repetitive regions")
    parser.add_option("--nd", dest="ndisc", type="int",
                      help="cutoff of minimum # of discordant pair")
    parser.add_option("--nfclip", dest="nfilterclip", type="int",
                      help="cutoff of minimum # of clipped reads in filtering step")
    parser.add_option("--nfdisc", dest="nfilterdisc", type="int",
                      help="cutoff of minimum # of discordant pair of each sample in filtering step")
    parser.add_option("--teilen", dest="teilen", type="int",
                      help="minimum length of the insertion for future analysis")

    parser.add_option("-o", "--output", dest="output",
                      help="The output file", metavar="FILE")
    (options, args) = parser.parse_args()
    return (options, args)


####
if __name__ == '__main__':
    (options, args) = parse_option()
    sf_id = options.id
    sf_bams = options.bam
    sf_bams_10X = "null"
    s_wfolder = options.wfolder
    sf_sbatch_sh = options.output
    if s_wfolder[-1] != "/":
        s_wfolder += "/"
    if os.path.exists(s_wfolder) == False:
        scmd = "mkdir {0}".format(s_wfolder)
        Popen(scmd, shell=True, stdout=PIPE).communicate()

    if os.path.isfile(sf_bams) == False:
        sf_bams = "null"
    if os.path.isfile(sf_bams_10X) == False:
        sf_bams_10X = "null"

    ncores = options.cores
    sf_folder_rep = options.lib  ##this is the lib folder path
    sf_ref=options.ref ####reference genome
    sf_folder_xtea=options.xtea

    l_rep_type=[]
    l_rep_type.append("L1")
    l_rep_type.append("Alu")
    l_rep_type.append("SVA")

    for rep_type in l_rep_type:
        sf_config=s_wfolder + rep_type+".config"
        gnrt_lib_config(sf_folder_rep, sf_ref, sf_folder_xtea, sf_config)

        s_wfolder_rep=s_wfolder+rep_type
        if os.path.exists(s_wfolder_rep)==False:
            cmd="mkdir {0}".format(s_wfolder_rep)
            Popen(cmd, shell=True, stdout=PIPE).communicate()

        s_head = gnrt_script_head()
        l_libs = load_par_config(sf_config)
        s_libs = gnrt_parameters(l_libs)
        ##
        iclip_c = options.nclip
        iclip_rp = options.cliprep
        idisc_c = options.ndisc
        iflt_clip = options.nfilterclip
        iflt_disc = options.nfilterdisc
        iflk_len = options.flklen
        itei_len = options.teilen
        iflag = options.flag

        s_calling_cmd = gnrt_calling_command(iclip_c, iclip_rp, idisc_c, iflt_clip, iflt_disc, ncores, iflk_len,
                                             itei_len, iflag)
        sf_sbatch_sh_rep=rep_type+"_"+sf_sbatch_sh
        gnrt_pipelines(s_head, s_libs, s_calling_cmd, sf_id, sf_bams, sf_bams_10X, s_wfolder_rep, sf_sbatch_sh_rep)

####